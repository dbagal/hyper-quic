import socket
import os
import configparser
import hashlib
import random
from exceptions import HyperQuicError

class HyperQuicSocket:

    class Config:
        def __init__(self) -> None:
            config = configparser.ConfigParser()
            
            current_dir = os.path.dirname(os.path.realpath(__file__))
            config_path = os.path.join(current_dir, "config.ini")
            config.read(config_path)
            for section in config.sections():
                for param, val in section.items():
                    setattr(self, param, val)

    
    class Buffer:
        def __init__(self, **params) -> None:
            for param, val in params.items():
                setattr(self, param, val)


    def __init__(self, host, port) -> None:

        self.hyper_quic_header_len = 25
        self.host, self.port = host, port
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sock.bind((host, port))


    def fragment(self, data):
        if type(data)==bytes:
            max_payload_size = self.config.max_payload_size - self.hyper_quic_header_len
            return [
                data[i:i+max_payload_size] 
                for i in range(0, len(str), max_payload_size)
            ]  
        else:
            raise HyperQuicError(
                msg = f"Fragmentation requires data to be in bytes format"
            )
        
    
    def get_connection_id(self):
        nonce = self.host + str(self.port) + str(random.random())
        return hashlib.sha256(nonce.encode()).digest()


    def send(self, data, to):
        fragments = self.fragment(data)