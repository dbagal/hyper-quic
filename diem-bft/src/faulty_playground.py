import random, datetime, string

import playground
import messages
from collections import defaultdict


class FaultyPlayground(playground.NetworkPlayground):

    def __init__(self, system_config, client_config, **params) -> None:
        super().__init__(**params)

        self.system_config = system_config
        self.client_config = client_config
        self.num_drops = defaultdict(int)
        

    def mock_payload_generator(self):
        """ 
        @function:
        - get a random string as the command with length specified in config file
        - the transaction has the form - (client_id, timestamp): command
        """
        def get_request():
            cmd_len = self.client_config.client_command_length
            cmd = ''.join(random.choices(string.ascii_uppercase + string.digits, k = cmd_len))
            current_ts = datetime.datetime.now().strftime("%m-%d-%Y::%H:%M:%S.%f")
            txn = f"({self.replica_id},{current_ts}): {cmd}"
            client = random.choice(self.client_config.client_id_set)
            return  messages.ClientRequest(
                txn = txn, 
                sender = self.replica_id, 
                sender_key=self.client_config.client_keys[client][0],
                log=False
            )

        num_commands = random.choice(range(10))
        return [get_request() for _ in range(num_commands)]
        

    def intercept_incoming_msg(self, msg, sender, receiver):
        return msg
        if msg.type == messages.Messages.PROPOSAL_MSG and self.num_drops[msg.type] < 5:
            self.num_drops[msg.type] += 1
            return None
        else:
            return msg


    def intercept_outcoming_msg(self, msg, sender, receiver):
        return msg
        if msg.type == messages.Messages.SYNC_REQUEST and self.num_drops[msg.type] < 5:
            self.num_drops[msg.type] += 1
            return None
        else:
            return msg


