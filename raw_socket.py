
import socket

class RawSocket:
    def __init__(self):
        self.host = socket.gethostbyname(socket.gethostname())
        self.raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        self.raw_socket.bind((self.host, 0))
        

    def send(self, data, dst_host, dst_port):
        self.raw_socket.connect((dst_host, dst_port));
        self.raw_socket.send(data)


    def receive(self, buffer_size=65536):
        return self.raw_socket.recvfrom(buffer_size)[0]