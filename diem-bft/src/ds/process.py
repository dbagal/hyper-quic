import socket, traceback
import pickle
import time
from threading import Thread
from collections import defaultdict
from ds.utils import fetch_id_components
from doq_client import send_data
import doq_server


class Process():
    def __init__(self, id) -> None:

        self.id = id
        self.process_name, self.ip, self.send_port, self.recv_port = fetch_id_components(self.id)
        self.send_queue = []
        # self.recv_queue = []

        self.send_ctr = defaultdict(int)
        self.recv_ctr = defaultdict(int)
        self.hbq = defaultdict(dict)

        # self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            # self.recv_sock.bind((self.ip, self.recv_port))
            Thread(target=doq_server.init_server, args=((self.ip, self.recv_port))).start()
        except:
            print(traceback.format_exc())
            print(self.id, self.recv_port)

        self.send_thread = Thread(target=self.__send_thread)
        self.recv_thread = Thread(target=self.__recv_thread)
        self.deliver_thread = Thread(target=self.__deliver_thread)
        self.send_thread.start()
        self.recv_thread.start()
        self.deliver_thread.start()

    class IncorrectPeerSetError(Exception):
        def __init__(self):
            msg = "Check the call to your process' super.setup() function; \
                the attribute peers = peer_id_set is mandatory for broadcast"
            super().__init__(msg)

    def setup(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def send(self, data, send_to):
        self.send_ctr[send_to] += 1
        seq_num = self.send_ctr[send_to]
        obj = (data, seq_num, self.id, send_to)
        self.send_queue.append(obj)

    def multicast(self, data, group):
        try:
            for process_id in group:
                self.send_ctr[process_id] += 1
                seq_num = self.send_ctr[process_id]
                obj = (data, seq_num, self.id, process_id)
                self.send_queue.append(obj)
        except AttributeError:
            raise Process.IncorrectPeerSetError()

    def broadcast(self, data):
        try:
            for process_id in self.peers:
                self.send_ctr[process_id] += 1
                seq_num = self.send_ctr[process_id]
                obj = (data, seq_num, self.id, process_id)
                self.send_queue.append(obj)
        except AttributeError:
            raise Process.IncorrectPeerSetError()

    def __send_thread(self):
        while True:
            if len(self.send_queue) > 0:
                obj = self.send_queue.pop(0)
                self.__send(obj)

    def __send(self, obj):
        (data, seq_num, sender, send_to) = obj
        process_name, send_to_ip, send_port, recv_port = fetch_id_components(send_to)

        # serialize the object for transmission
        serialized_obj = pickle.dumps(obj) + b"/EOM"

        try:
            # send_data(serialized_obj)
            # send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # send_sock.connect((send_to_ip, recv_port))
            # send_sock.sendall(serialized_obj)
            # send_sock.close()
            print(f'Sending data = {serialized_obj}')
            send_data(send_to_ip, recv_port, serialized_obj)

        except:
            # set connection status and recreate socket  
            connected = False
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            send_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            while not connected:
                # attempt to reconnect, otherwise sleep for 0.5 seconds  
                try:
                    send_sock.connect((send_to_ip, recv_port))
                    connected = True
                except socket.error:
                    time.sleep(0.01)

            send_sock.sendall(serialized_obj)
            send_sock.close()

    def __recv_thread(self):
        pass
        # keep listening for requests on the receive port of the process
        # self.recv_sock.listen(1)
        # while True:
        #     try:
        #         sender_sock, sender_addr = self.recv_sock.accept()
        #     except:
        #         break
        #
        #     obj = self.__recv(sender_sock)
        # self.recv_queue += [obj]

    def __recv(self, sender_sock):
        def recvall(sock):
            data = b""
            while True:
                data_chunk = sock.recv(4096)
                data += data_chunk
                if data_chunk.endswith(b"/EOM"):
                    data = data[:-1]
                    break
            return data

        data = pickle.loads(recvall(sender_sock).strip(b"/EOM"))
        return data

    def __deliver_thread(self):
        while True:
            if doq_server.recv_queue_len() > 0:
                print(f'length of recv queue in process = {doq_server.recv_queue_len()}')
                print(f'RECV QUEUE PROCESS = {doq_server.recv_queue}')
                obj = doq_server.recv_queue_pop(0)
                self.__deliver(obj)

    def __deliver(self, obj):
        print(f'########DELIVERED######## = {obj}')
        (data, seq_num, sender_id, receiver_id) = obj
        if self.recv_ctr[sender_id] + 1 == seq_num:
            self.recv_ctr[sender_id] += 1
            self.receive(data, sender_id)

            ctr = seq_num + 1
            while True:
                if ctr in self.hbq[sender_id].keys():
                    (data, seq_num, sender, receiver) = self.hbq[sender_id][ctr]
                    self.receive(data, sender)
                    del self.hbq[sender_id][ctr]
                    ctr += 1
                else:
                    break
        else:
            self.hbq[sender_id][seq_num] = obj

        print(f'%%%%%%%%%%%DELIVERY ENDED%%%%%%%%%')