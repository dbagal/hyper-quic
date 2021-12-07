import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ds.process import Process

class P(Process):

    def __init__(self, id, process_id_set):
        Process.__init__(self, id)
        super().setup(peers = process_id_set)
        
        data = input("Data: ")
        obj = {"data":data}

        while data!="exit":
            self.broadcast(obj)
            #self.send(data=obj, to=random.choice(list(self.process_ids)))
            data = input("Data: ")
            obj = {"data":data}

    def receive(self, msg, sender_addr):
        print(f"\nMessage: {msg} sent by {sender_addr}")


ip="localhost"
pset = [f"p1@{ip}:8000:8001", f"p2@{ip}:8002:8003", f"p3@{ip}:8004:8005"]#, "p3@172.24.16.54:8006:8007"]
peers = set(pset)

p = P(pset[0], peers)