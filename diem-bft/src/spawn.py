import multiprocessing, os, shutil

import time
import config
from replica import Replica
from client import Client
import faulty_playground


class Spawn:

    def __init__(self) -> None:

        self.system_config = config.SystemConfig()
        self.client_config = config.ClientConfig()
        
        self.setup()


    def setup(self):

        src_dir = os.path.dirname(os.path.realpath(__file__))
        root_dir = os.path.dirname(src_dir)

        ledger_folder_path = os.path.join(root_dir, "ledger")
        logs_folder_path = os.path.join(root_dir, "logs")

        shutil.rmtree(ledger_folder_path)
        shutil.rmtree(logs_folder_path)
        
        if not os.path.exists(ledger_folder_path): os.makedirs(ledger_folder_path)
        if not os.path.exists(logs_folder_path): os.makedirs(logs_folder_path)

        src_dir = os.path.dirname(os.path.realpath(__file__))
        parent_dir = os.path.dirname(src_dir)
        block_tree_logs = os.path.join(parent_dir, "logs", "block-trees")
        if not os.path.exists(block_tree_logs):
            os.makedirs(block_tree_logs)

    def spawn_replicas(self, rid, keys, playground):
        replica = Replica(rid, keys, playground=playground)
        replica.start_processing()


    def spawn_clients(self, cid, keys, notify_queue):
        client = Client(cid, keys, notify_queue=notify_queue)
        client.start_processing()


    def spawn(self):
        replica_id_set = self.system_config.replica_id_set
        client_id_set = self.client_config.client_id_set

        notify_queue = multiprocessing.Queue()

        replicas = []
        for i in range(self.system_config.num_validators):
            rid = replica_id_set[i]
            
            keys = {
                "private-key":self.system_config.replica_keys[rid][0],
                "public-keys":{
                    **{
                        r:k[1] for r,k in self.system_config.replica_keys.items() 
                    },
                    **{
                        r:k[1] for r,k in self.client_config.client_keys.items()
                    }
                }
            }
            playground = None
            if i>2*self.system_config.num_byzantine:
                playground = faulty_playground.FaultyPlayground(
                    system_config=self.system_config,
                    client_config= self.client_config, 
                )
            
            r = multiprocessing.Process(target=self.spawn_replicas, args=(rid, keys, playground))
            replicas += [r]
            r.start()
        
        print("All replicas up!")

        time.sleep(2)
        clients = []
        for i in range(self.client_config.num_clients):
            cid = client_id_set[i]
            keys = {
                "private-key":self.client_config.client_keys[cid][0],
                "public-keys":{
                    r:k[1] for r,k in self.system_config.replica_keys.items() 
                }
            }
            c = multiprocessing.Process(target=self.spawn_clients, args=(cid, keys, notify_queue))
            clients += [c]
            c.start()

        print("All clients up!\n")

        notifications = set()
        
        while True:
            notifications.add(notify_queue.get())
            if len(notifications) == self.client_config.num_clients:
                break
        
        for node in replicas+clients:
            node.terminate()

        for node in replicas:
            node.join()

        for node in clients:
            node.join()

        print("DONE")
        

if __name__=="__main__":
    executor = Spawn()
    executor.spawn()