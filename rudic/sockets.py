import os
import configparser
import socket

from rudic.packet import RUDICPacket


class RUDICError(Exception):
    def __init__(self, msg) -> None:
        super().__init__(msg)


class RUDICSocket:
    def __init__(self, host, port) -> None:
        self.rudic_header_len = 9
        self.host, self.port = host, port
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sock.bind((host, port))


    class Config:
        def __init__(self) -> None:
            config = configparser.ConfigParser()
            
            self.current_dir = os.path.dirname(os.path.realpath(__file__))
            config_path = os.path.join(self.current_dir, "config.ini")
            config.read(config_path)
            for section in config.sections():
                for param, val in section.items():
                    setattr(self, param, val)


    def fragment(self, data):
        if type(data)==bytes:
            max_payload_size = self.config.max_payload_size - self.rudic_header_len
            return [
                data[i:i+max_payload_size] 
                for i in range(0, len(str), max_payload_size)
            ]  
        else:
            raise RUDICError(
                msg = f"Fragmentation requires data to be in bytes format"
            )
     

    def send(self, data, addr):
        fragments = self.fragment(data)
        rudic_packets = []
        for i,payload in enumerate(fragments):
            rudic_packets += [
                RUDICPacket(
                    flags=[0,0,0,0,0,0,0,0],
                    packet_num=i+1,
                    look_ahead_packet_num=len(fragments)-1,
                    payload=payload
                )
            ]
        for packet in rudic_packets:
            se