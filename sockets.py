import socket
import os, json
import configparser
import hashlib
import random
import pickle
from collections import defaultdict
import threading
from exceptions import HyperQuicError
from packet import HyperQuicPacket, HyperQuicPacketHandler
from crypto import Crypto

class HyperQuicServerSocket:

    class Config:
        def __init__(self) -> None:
            config = configparser.ConfigParser()
            
            self.current_dir = os.path.dirname(os.path.realpath(__file__))
            config_path = os.path.join(self.current_dir, "config.ini")
            config.read(config_path)
            for section in config.sections():
                for param, val in section.items():
                    setattr(self, param, val)

    
    class Buffer:
        def __init__(self, **params) -> None:
            for param, val in params.items():
                setattr(self, param, val)


    def __init__(self, host, port, global_clock) -> None:
        
        self.config = HyperQuicSocket.Config()
        self.hyper_quic_header_len = 25
        self.host, self.port = host, port
        self.global_clock = global_clock
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sock.bind((host, port))

        self.snd_buffer = defaultdict(list)
        self.rcv_buffer = defaultdict(list)

        self.connections = dict()
        self.cache = dict() 

        self.public_key = Crypto.get_prime_number(self.config.key_range)
        self.private_key = Crypto.get_prime_number(self.config.key_range)


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
        return hashlib.sha256(nonce.encode()).digest()[0:64]


    def establish_connection(self, dst_ip, dst_port):
        if self.cache.get((dst_ip, dst_port), None) is None:
            ichlo_packet = HyperQuicPacket(
                connection_id=b"",
                flags = [1,0,0,0,0,0,0,0],
                packet_num = -1,
                payload = pickle.dumps(
                    {
                        "public-key": self.public_key
                    }
                )
            )
            ichlo_packet_bytes = HyperQuicPacketHandler.assemble(ichlo_packet)
            self.sock.sendto(ichlo_packet_bytes, (dst_ip, dst_port))
            timer = threading.Timer(
                interval = self.config.connection_establishment_timer, 
                function = self.establish_connection, args=((dst_ip, dst_port))
            )
            timer.start()



    def send(self, data, to, connection_id):
        fragments = self.fragment(data)

        """ for payload in fragments:
        hyper_quic_packet = HyperQuicPacket(
            connection_id=connection_id,
            flags = flag_list,
            packet_num= pnum,
            payload = payload
        ) """


    def recv(self):
        while True:
            raw_bytes, addr = self.sock.recvfrom(65536)
            hyper_quic_packet = HyperQuicPacketHandler.disassemble(raw_bytes)
            if hyper_quic_packet.flags.ichlo == 1:
                conn_id = self.get_connection_id()



class HyperQuicClientSocket:


    class Config:
        def __init__(self) -> None:
            config = configparser.ConfigParser()
            
            self.current_dir = os.path.dirname(os.path.realpath(__file__))
            config_path = os.path.join(self.current_dir, "config.ini")
            config.read(config_path)
            for section in config.sections():
                for param, val in section.items():
                    setattr(self, param, val)


    def __init__(self, host, port) -> None:
        
        self.config = HyperQuicClientSocket.Config()
        self.hyper_quic_header_len = 25
        self.host, self.port = host, port
        
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sock.bind((host, port))

        self.snd_buffer = []
        self.rcv_buffer = []
        self.timer = None

        self.current_dir = os.path.dirname(os.path.realpath(__file__))
        self.cache_path = os.path.join(self.current_dir, "cache.json")
        
        with open(self.cache_path, "r") as fp:
            self.cache = json.load(fp) 

        self.public_key = Crypto.get_prime_number(self.config.key_range)
        self.private_key = Crypto.get_prime_number(self.config.key_range)
        self.partial_key = None


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
        

    def establish_connection(self, dst_ip, dst_port):
        if self.cache.get((dst_ip, dst_port), None) is None:
            ichlo_packet = HyperQuicPacket(
                connection_id=b"",
                flags = [1,0,0,0,0,0,0,0],
                packet_num = -1,
                payload = pickle.dumps(
                    {
                        "public-key": self.public_key
                    }
                )
            )
            ichlo_packet_bytes = HyperQuicPacketHandler.assemble(ichlo_packet)
            self.sock.sendto(ichlo_packet_bytes, (dst_ip, dst_port))

            if self.timer is not None:
                self.timer.cancel()

            self.timer = threading.Timer(
                interval = self.config.connection_establishment_timer, 
                function = self.establish_connection, args=((dst_ip, dst_port))
            )
            self.timer.start()



    def send(self, data, to, connection_id):
        fragments = self.fragment(data)

        """ for payload in fragments:
        hyper_quic_packet = HyperQuicPacket(
            connection_id=connection_id,
            flags = flag_list,
            packet_num= pnum,
            payload = payload
        ) """


    def process_rej_msg(self, hyper_quic_packet):
        conn_id = hyper_quic_packet.connection_id
        payload = pickle.loads(hyper_quic_packet.payload)

        dst_ip = payload["dst-ip"]
        dst_port = payload["dst-port"]

        if self.timers.get((dst_ip, dst_port), None) is not None:
            self.timers[(dst_ip, dst_port)].cancel()

        self.cache[(dst_ip, dst_port)] = {
            "connection-id": conn_id,
            "server-public-key": payload["server-public-key"],
            "partial-key": payload["partial-key"]
        }

        self.partial_key = payload["partial-key"]

        with open(self.cache_path, "w") as fp:
            json.dump(self.cache, fp)


    def process_shlo_msg(self, hyper_quic_packet):
        payload = pickle.loads(hyper_quic_packet.payload)

        dst_ip = payload["dst-ip"]
        dst_port = payload["dst-port"]

        if self.timers.get((dst_ip, dst_port), None) is not None:
            self.timers[(dst_ip, dst_port)].cancel()


    def recv(self):
        while True:
            raw_bytes, addr = self.sock.recvfrom(65536)
            hyper_quic_packet = HyperQuicPacketHandler.disassemble(raw_bytes)

            if hyper_quic_packet.flags.rej == 1:
                self.process_rej_msg(hyper_quic_packet)

            if hyper_quic_packet.flags.shlo == 1:
                self.process_shlo_msg(hyper_quic_packet)
