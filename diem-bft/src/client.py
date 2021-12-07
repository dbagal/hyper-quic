import argparse
import datetime
import random
import string
import time, sys, os
from collections import Counter, defaultdict
from threading import Timer

import config
from ds.process import Process
from messages import ClientRequest, Messages
import utils
import crypto

class Client(Process):

    def __init__(self, id, keys, **params) -> None:
        Process.__init__(self, id)
        self.client_config = config.ClientConfig()
        super().setup(peers=self.client_config.replica_id_set)

        self.private_key = keys["private-key"]
        self.public_keys = keys["public-keys"]

        for param,val in params.items():
            setattr(self, param, val)

        self.id = id

        current_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(current_dir)

        log_file = self.id.split("@")[0]
        fname1 = os.path.join(parent_dir, "logs", f"{log_file}.log")
        fname2 = os.path.join(parent_dir, "logs", "block-trees", f"{log_file}.log")

        if not os.path.exists(os.path.dirname(fname1)): os.makedirs(os.path.dirname(fname1))
        if not os.path.exists(os.path.dirname(fname2)): os.makedirs(os.path.dirname(fname2))

        utils.setup_logger(f"{log_file}", fname1)
        utils.setup_logger(f"{log_file}-block-tree", fname2)

        #utils.set_loggers(id)
        
        utils.log(
            id = self.id,
            msg = f"Client up (\n\tclient-id: {self.id}\n)"
        )

        self.requests_sent = defaultdict(int) # msg: count
        self.collected_responses = defaultdict(set) # msg: {resp1, resp2}
        self.transactions = dict() # msg: txn
        self.timers = dict() # msg: timer
        self.responses = dict()


    def form_request(self):
        """ 
        @function:
        - get a random string as the command with length specified in config file
        - the transaction has the form - (client_id, timestamp): command
        """
        cmd = ''.join(random.choices(string.ascii_uppercase +
                             string.digits, k = self.client_config.client_command_length))
        current_ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
        txn = f"({self.id},{current_ts}): {cmd}"
        
        client_request =  ClientRequest(
            txn = txn, 
            sender = self.id, 
            sender_key=self.private_key
        )
        self.transactions[client_request.id] = txn

        return client_request

    
    def send(self, msg, send_to):
        if hasattr(self, "playground") and self.playground is not None:
            sender = self.id
            receiver = send_to
            msg = self.playground.intercept_outgoing_msg(msg, sender, receiver)
            if msg is not None:
                super().send(msg, send_to)
        else:
            super().send(msg, send_to)

    
    def broadcast(self, msg):
        if hasattr(self, "playground") and self.playground is not None:
            sender = self.id
            group = []
            msgs = []
            for rid in self.peers:
                modified_msg = self.playground.intercept_outgoing_msg(msg, sender, rid)
                if modified_msg is not None:
                    group += [rid]
                    msgs += [modified_msg]
            if len(group)>0:
                for msg, replica in zip(msgs, group):
                    super().send(msg, replica)
        else:
            super().broadcast(msg)


    def start_processing(self):
        """  
        @function:
        - periodically send a command to the system for num_commands_to_be_sent times
        - between each command, wait for a random amount of time
        - start a timer to ensure timely response
        """
        wait_time_in_seconds = [0.05, 0.1, 0.15]
        
        for _ in range(self.client_config.num_commands_to_be_sent):
            msg = self.form_request()
            self.broadcast(msg)
            self.timers[msg.id] = Timer(self.client_config.client_wait_before_retransmit,
                                         self.on_timeout, args=[msg])
            self.timers[msg.id].start()
            self.requests_sent[msg.id] += 1

            if self.client_config.send_concurrent_requests == "true":
                time.sleep(0.1)
            elif self.client_config.send_concurrent_requests == "false":
                time.sleep(random.choice(wait_time_in_seconds))
        
        if hasattr(self, "notify_queue"):
            # on receiving responses to all the results, send shutdown notification
            while len(self.responses)!=self.client_config.num_commands_to_be_sent:
                pass

            self.notify_queue.put(self.id)
            sys.exit()
        

    def get_consistent_response(self, msg_id):
        """  
        @function:
        - for a msg indexed by msg_id, determine the number of identical responses it has received
        - if this number is f+1, return the result
        """
        similar_responses_and_count = [
            (item,count) 
            for item, count in Counter(
                [resp.ledger_state_hash for resp in self.collected_responses[msg_id]]
            ).items()
        ]

        for result, count in similar_responses_and_count:
            if count == (self.client_config.num_byzantine+1):
                return result
        return None

    
    def receive(self, msg, sender):

        if hasattr(self, "playground") and self.playground is not None:
            receiver = self.id
            msg = self.playground.intercept_incoming_msg(msg, sender, receiver)
            if msg is not None:
                self.process_msg(msg, sender)
        else:
            self.process_msg(msg, sender)


    def process_msg(self, msg, sender):

        if crypto.Crypto.is_valid(msg, self.public_keys[sender]) and msg.type==Messages.CLIENT_RESPONSE:
            
            # process the response only if the result hasn't yet been received earlier
            if self.responses.get(msg.id, None) is None:
                
                # collect the response received from the replicas
                self.collected_responses[msg.id].add(msg)

                # check if there's a consistent result
                result = self.get_consistent_response(msg.id)
                if result is not None:

                    # save the result for the request
                    self.responses[msg.id] = result

                    try:
                        # cancel the timer for the request if it is set
                        self.timers[msg.id].cancel()
                    except:
                        # some byzantine nodes might send random replies to requests which clients haven't even made
                        pass

                    # clear all collected responses
                    del self.collected_responses[msg.id]

                    ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
                    utils.log(
                        id = self.id,
                        msg = f"f+1 identical responses received, result deduced \
                            (\n\trequest-id: {msg.id}, \n\ttxn:{self.transactions[msg.id]} \
                            \n\tresult: {result}, \n\ttimestamp: {ts}\n)"
                    ) 


    def on_timeout(self, msg):
        
        # limit retransmissions
        if  self.requests_sent[msg.id] > self.client_config.num_retransmissions-1:
            return

        # Retransmit the msg
        self.broadcast(msg)

        utils.log(
            id = self.id, 
            msg = f"Retransmitting request (\n\trequest-id: {msg.id}, \n\ttxn: {msg.transaction}\n)"
        )

        # Reset timer
        self.timers[msg.id] = Timer(self.client_config.client_wait_before_retransmit,
                                         self.on_timeout, args=[msg])

        # Clear collected responses
        self.collected_responses[msg.id].clear()

        self.requests_sent[msg.id] += 1


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("id")
    args = parser.parse_args()
    id = args.id
    replica = Client(id)