import sys, os, datetime
from collections import defaultdict
current_dir = os.path.dirname(os.path.realpath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import playground
import messages
import utils


class ClientPlayground(playground.NetworkPlayground):

    def __init__(self, node_id, client_config, **params) -> None:
        super().__init__(**params)
    
        self.id = node_id
        self.client_config = client_config

        for param, val in params.items():
            setattr(self, param, val)

        # store all requests and its responses in transaction_history
        self.transaction_history = dict()
        self.num_responses_rcvd = 0


    def intercept_outgoing_msg(self, msg, sender, receiver):
        """  
        @function:
        - record the request being sent out and its metadata in 'transaction_history'
        """

        # record the metadata of the original request and NOT the retransmitted one
        if msg.type == messages.Messages.CLIENT_REQUEST and self.transaction_history.get(msg.id, None) is None:
            txn = msg.transaction
            cid, ts, cmd = utils.get_transaction_components(txn)

            self.transaction_history[msg.id] = {
                "cmd": cmd,
                "ts": ts,
                "response-counts": defaultdict(int),
                "response": None,
                "response-ts": None
            }

        return msg


    def intercept_incoming_msg(self, msg, sender, receiver):
        """  
        @function:
        - on receiving a response, if f+1 identical responses are received, update the metadata of the request in the transaction history
        """
        if msg.type == messages.Messages.CLIENT_RESPONSE:
            try:
                self.transaction_history[msg.id]["response-counts"][msg.ledger_state_hash] += 1
                
                if self.transaction_history[msg.id]["response-counts"][msg.ledger_state_hash] == self.client_config.num_byzantine+1:
                    
                    self.transaction_history[msg.id]["response"] = msg.ledger_state_hash
                    ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
                    self.transaction_history[msg.id]["response-ts"] = ts

                    sent_ts = datetime.datetime.strptime(self.transaction_history[msg.id]["ts"], "%m-%d-%Y::%H:%M:%S.%f") 
                    rcvd_ts = datetime.datetime.strptime(ts, "%m-%d-%Y::%H:%M:%S.%f")
                    t_delta = (rcvd_ts - sent_ts).total_seconds()

                    self.transaction_history[msg.id]["response-time"] = str(t_delta)+" secs"

                    self.num_responses_rcvd += 1
                    del self.transaction_history[msg.id]["response-counts"]

                    utils.log_playground(
                        id = self.id,
                        msg = f"Client request metadata (\n{utils.get_string_representation(self.transaction_history[msg.id])}\n)"
                    )

                    # inform executor of the receipt of f+1 identical responses
                    self.notify_queue.put(self.transaction_history[msg.id])

                    del self.transaction_history[msg.id]
                    
            except:
                pass

        return msg
