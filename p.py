import os, sys
from process import Process

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


own_ip = "172.24.19.162"
other_ip = "172.24.22.2"
p1ip = f"p1@{own_ip}:8000:8001"
p2ip = f"p2@{other_ip}:8000:8001"
peers = {p1ip, p2ip}

p = P(p1ip, peers)