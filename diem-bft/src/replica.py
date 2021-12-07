import argparse, os

from ds.process import Process
import config
import leader_election
import messages
import main
import safety
import utils
import crypto


class Replica(Process):

    def __init__(self, id, keys, **params) -> None:
        Process.__init__(self, id)

        for param,val in params.items():
            setattr(self, param, val)

        self.replica_id = id
        self.system_config = config.SystemConfig()
        super().setup(peers=self.system_config.replica_id_set)

        main.Main._replica = self

        # set up signing keys
        safety.Safety.private_key = keys["private-key"]
        safety.Safety.public_keys = keys["public-keys"]

        current_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(current_dir)

        log_file = self.replica_id.split("@")[0]
        fname1 = os.path.join(parent_dir, "logs", f"{log_file}.log")
        fname2 = os.path.join(parent_dir, "logs", "block-trees", f"{log_file}.log")

        if not os.path.exists(os.path.dirname(fname1)): os.makedirs(os.path.dirname(fname1))
        if not os.path.exists(os.path.dirname(fname2)): os.makedirs(os.path.dirname(fname2))

        utils.setup_logger(f"{log_file}", fname1)
        utils.setup_logger(f"{log_file}-block-tree", fname2)

        #utils.set_loggers(id)
        leader_election.LeaderElection.validators= self.peers
        leader_election.LeaderElection.window_size = self.system_config.window_size
        leader_election.LeaderElection.exclude_size = self.system_config.exclude_size

        for param,val in params.items():
            setattr(self, param, val)

        utils.log(
            id = self.replica_id,
            msg = f"Replica up (\n\treplica-id: {self.replica_id}\n)"
        )


    def start_processing(self):
        main.Main.start()


    def configure(self, **params):
        for param,val in params.items():
            setattr(self, param, val)


    def send(self, msg, send_to):

        if hasattr(self, "playground") and self.playground is not None:
            sender = self.replica_id
            receiver = send_to
            modified_msg = self.playground.intercept_outgoing_msg(msg, sender, receiver)
            if modified_msg is not None:
                super().send(modified_msg, send_to)
        else:
            super().send(msg, send_to)

    
    def broadcast(self, msg):
        if hasattr(self, "playground") and self.playground is not None:
            sender = self.replica_id
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

        
    def receive(self, msg, sender):

        if hasattr(self, "playground") and self.playground is not None:
            receiver = self.replica_id
            msg = self.playground.intercept_incoming_msg(msg, sender, receiver)
            if msg is not None:
                self.process_msg(msg, sender)
        else:
            self.process_msg(msg, sender)


    def process_msg(self, msg, sender):
        
        if crypto.Crypto.is_valid(msg, safety.Safety.public_keys[sender]):
            if msg.type==messages.Messages.CLIENT_REQUEST:
                utils.log(
                    id = self.replica_id,
                    msg = f"CLIENT-REQUEST received from {msg.sender}(\n{msg.log()}\n)"
                ) 
                main.Main.process_client_request(msg)

            elif msg.type == messages.Messages.VOTE_MSG:
                utils.log(
                    id = self.replica_id, 
                    msg = f"VOTE-MSG received from {msg.sender}(\n{msg.log()}\n)"
                )
                main.Main.process_vote_msg(msg)

            elif msg.type == messages.Messages.TIMEOUT_MSG:
                utils.log(
                    id = self.replica_id, 
                    msg = f"TIMEOUT-MSG received from {msg.sender}(\n{msg.log()}\n)"
                )
                main.Main.process_timeout_msg(msg)

            elif msg.type == messages.Messages.PROPOSAL_MSG:
                utils.log(
                    id = self.replica_id, 
                    msg = f"PROPOSAL-MSG received from {msg.block.author}(\n{msg.log()}\n)"
                )
                main.Main.process_proposal_msg(msg)

            elif msg.type == messages.Messages.SYNC_REQUEST:
                utils.log(
                    id = self.replica_id, 
                    msg = f"SYNC-REQUEST received from {msg.sender}(\n{msg.log()}\n)"
                )
                main.Main.process_sync_request(msg)

            elif msg.type == messages.Messages.SYNC_RESPONSE:
                utils.log(
                    id = self.replica_id, 
                    msg = f"SYNC-RESPONSE received from {msg.sender}(\n{msg.log()}\n)"
                )
                main.Main.process_sync_response(msg)



if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("id")
    args = parser.parse_args()
    id = args.id # name @ ip : sport : rport
    replica = Replica(id)