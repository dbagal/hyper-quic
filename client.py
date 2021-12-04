import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

from scapy.all import *
from scapy.layers.inet import IP
from raw_socket import RawSocket

sock = RawSocket()

pack = IP(dst="127.0.0.1")/b"hello how are you?"
sock.send(bytes(pack))

pack = IP(dst="127.0.0.1")/b"hello how are you? hello how are you? hello how are you? hello how are you? hello how are you? hello how are you?"
sock.send(bytes(pack))


