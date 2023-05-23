import socket
import threading
import select
import time

SOCKET_LIST = []
TO_BE_SENT = []
SENT_BY = {}


class Server(threading.Thread):
    def __init__(self):
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.bind(('localhost', 5535))
        self.sock.listen(2)
        SOCKET_LIST.append(self.sock)
        print("Server started on port 5535")

    def run(self):
        while True:
            try:
                read, _, err = select.select(SOCKET_LIST, [], [], 0)
                for sock in read:
                    if sock == self.sock:
                        sockfd, addr = self.sock.accept()
                        print(f"New client connected from {addr}")
                        SOCKET_LIST.append(sockfd)
                    else:
                        s = sock.recv(2048)
                        TO_BE_SENT.append(s)
                        SENT_BY[s] = sock
            except Exception as e:
                print(f"Client {sock.getpeername()} disconnected")
                SOCKET_LIST.remove(sock)


class HandleConnections(threading.Thread):
    def run(self):
        while True:
            try:
                _, write, _ = select.select([], SOCKET_LIST, [], 0)
                for data in list(TO_BE_SENT):
                    for sock in write:
                        if sock != SENT_BY.get(data):
                            print(
                                f"Sending {len(data)} bytes to {sock.getpeername()}")
                            try:
                                sock.send(data)
                            except Exception as e:
                                print(
                                    f"Error occurred while sending data to {sock.getpeername()}: {e}")
                                continue
                    time.sleep(0.1)
                    TO_BE_SENT.remove(data)
                    del SENT_BY[data]
            except Exception as e:
                print(f"Error occurred while writing to socket: {e}")


if __name__ == '__main__':
    server = Server()
    server.start()

    handler = HandleConnections()
    handler.start()
