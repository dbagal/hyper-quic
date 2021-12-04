import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
from scapy.layers.inet import IP
from raw_socket import RawSocket

print("starting...")
ip = '172.24.19.162'
port = 8000
sock = RawSocket(host=ip)

for i in range(2):
    print("listening")
    data = sock.receive()
    pack = IP(data)
    a = bytes(pack[IP].payload)
    print(a[20:])
    
    