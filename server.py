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
