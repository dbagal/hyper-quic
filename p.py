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


ip="p1@localhost:8000:8001"
p = P(ip)