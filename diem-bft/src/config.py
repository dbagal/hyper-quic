import os
import json


class SystemConfig:
    def __init__(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(current_dir)
        
        with open(os.path.join(parent_dir, "config", "config.json")) as json_file:
            config = json.load(json_file)

        system_config = config["system"]
        for key, value in system_config.items():
            setattr(self, key, value)

        self.replica_id_set = self.replica_id_set[0:self.num_validators]
        self.replica_keys = {rid:self.replica_keys[rid] for rid in self.replica_id_set}

        current_dir = os.path.dirname(os.path.realpath(__file__))
        root_dir = os.path.dirname(current_dir)

        self.ledger_paths = {
            id:os.path.join(root_dir, "ledger", ledger_path) 
            for id, ledger_path in self.ledger_paths.items() 
        }


class ClientConfig:
    def __init__(self):
        current_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(current_dir)

        with open(os.path.join(parent_dir, "config", "config.json")) as json_file:
            config = json.load(json_file)

        client_config = config["client"]
        for key, value in client_config.items():
            setattr(self, key, value)

        self.num_byzantine = config["system"]["num_byzantine"]
        self.num_validators = config["system"]["num_validators"]
        self.replica_id_set = config["system"]["replica_id_set"][0:self.num_validators]
        self.client_id_set = self.client_id_set[0:self.num_clients]
        self.client_keys = {cid:self.client_keys[cid] for cid in self.client_id_set}


