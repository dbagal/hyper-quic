import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import *
from scapy.layers.inet import IP
from raw_socket import RawSocket

ip = '172.24.19.162'
server_ip = '172.24.22.2'
sock = RawSocket(host=ip)

pack = IP(src=ip, dst=server_ip)/b"hello how are you?"
sock.send(bytes(pack), server_ip)

#sock = RawSocket(host=ip)
pack = IP(src=ip, dst=server_ip)/b"hello how are you? hello how are you? hello how are you? hello how are you? hello how are you? hello how are you?"
sock.send(bytes(pack), server_ip)


