import socket
import os
import configparser
import hashlib
import random
from exceptions import HyperQuicError

class HyperQuicProcess:

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

        self.config = HyperQuicProcess.Config()
        self.host, self.port = host, port
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sock.bind((host, port))


    def fragment(self, data):
        if type(data)==bytes:
            return [
                data[i:i+self.config.max_payload_size] 
                for i in range(0, len(str), self.config.max_payload_size)
            ]  
        else:
            raise HyperQuicError(
                msg = f"Fragmentation requires data to be in bytes format"
            )
        
    
    def get_connection_id(self):
        nonce = self.host + str(self.port) + str(random.random())
        return hashlib.sha256(nonce.encode()).hexdigest()