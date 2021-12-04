
import socket

class RawSocket:
    def __init__(self, host):
        self.host = host
        self.raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        self.raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        

    def send(self, data, dst_host):
        try:
            self.raw_socket.connect((dst_host,0));
            self.raw_socket.send(data)
        except:
            self.raw_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
            self.raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.raw_socket.connect((dst_host,0));
            self.raw_socket.send(data)


    def receive(self, buffer_size=65536):
        return self.raw_socket.recvfrom(buffer_size)[0]