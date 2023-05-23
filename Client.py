#! /usr/bin/env python

import socket
import time
import threading
import select
import json
import random
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

simetric_key = None
private_key = None
public_key_extern = None
fernet = None
public_key_bytes = None
send_public_key = True


class Server(threading.Thread):
    def initialise(self, receive):
        self.receive = receive

    def run(self):
        global simetric_key
        global private_key
        global public_key_extern
        global fernet
        global send_public_key
        global public_key_bytes
        lis = []
        lis.append(self.receive)
        while True:
            read, write, err = select.select(lis, [], [])
            for item in read:
                try:
                    chunk = item.recv(2048)
                    if chunk != '':
                        try:
                            data = json.loads(chunk.decode())
                            if data['tag'] == 'PK':
                                send_public_key = False
                                bytes_PKE = data['content'].encode()
                                public_key_extern = serialization.load_pem_public_key(
                                    bytes_PKE)
                                if simetric_key is None:
                                    simetric_key = Fernet.generate_key()
                                    fernet = Fernet(simetric_key)
                                    print("P2P Criptografado")
                                simetric_key_encrypted = public_key_extern.encrypt(
                                    simetric_key,
                                    padding.OAEP(
                                        mgf=padding.MGF1(
                                            algorithm=hashes.SHA256()),
                                        algorithm=hashes.SHA256(),
                                        label=None
                                    )
                                )
                                encrypted_hash = private_key.sign(
                                    simetric_key,
                                    padding.PSS(
                                        mgf=padding.MGF1(hashes.SHA256()),
                                        salt_length=padding.PSS.MAX_LENGTH
                                    ),
                                    hashes.SHA256()
                                )
                                json_data = json.dumps(
                                    {
                                        'tag': 'SK',
                                        'simetric_key_encrypted': simetric_key_encrypted.hex(),
                                        'public_key_bytes': public_key_bytes.decode(),
                                        'encrypted_hash': encrypted_hash.hex()
                                    })
                                self.receive.sendall(json_data.encode())

                            elif data['tag'] == 'SK' and simetric_key is None:
                                try:
                                    bytes_encrypted = bytes.fromhex(
                                        data['simetric_key_encrypted'])
                                    simetric_key = private_key.decrypt(
                                        bytes_encrypted,
                                        padding.OAEP(
                                            mgf=padding.MGF1(
                                                algorithm=hashes.SHA256()),
                                            algorithm=hashes.SHA256(),
                                            label=None
                                        )
                                    )
                                    bytes_PKE = data['public_key_bytes'].encode(
                                    )
                                    public_key_extern = serialization.load_pem_public_key(
                                        bytes_PKE)
                                    bytes_encrypted = bytes.fromhex(
                                        data['encrypted_hash'])
                                    public_key_extern.verify(
                                        bytes_encrypted,
                                        simetric_key,
                                        padding.PSS(
                                            mgf=padding.MGF1(
                                                hashes.SHA256()),
                                            salt_length=padding.PSS.MAX_LENGTH
                                        ),
                                        hashes.SHA256()
                                    )
                                    fernet = Fernet(simetric_key)
                                    print("P2P Criptografado")
                                except:
                                    simetric_key = None

                            elif data['tag'] == 'encrypted' and fernet is not None:
                                msg = fernet.decrypt(data['content'])
                                msg = msg.decode()
                                print(msg + '\n>>')
                        except:
                            pass
                except:
                    print("lost connection")
                    time.sleep(1)
                    break


class Client(threading.Thread):
    def connect(self, host, port):
        self.sock.connect((host, port))

    def client(self, msg):
        self.sock.send(msg)

    def run(self):
        global simetric_key
        global private_key
        global fernet
        global public_key_bytes
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            host = input("Enter the server IP \n>>")
            port = int(input("Enter the server Destination Port\n>>"))
        except EOFError:
            print("Error")
            return 1
        print("Connecting\n")
        self.connect(host, port)
        print("Connected\n")
        user_name = input("Enter the User Name to be Used\n>>")
        time.sleep(1)
        srv = Server()
        srv.initialise(self.sock)
        srv.daemon = True

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        public_key_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        json_data = json.dumps(
            {'tag': 'PK', 'content': public_key_bytes.decode()})

        print("Starting service")
        srv.start()
        time.sleep(1)

        if send_public_key:
            self.client(json_data.encode())

        while True:
            try:
                if fernet is not None:
                    msg = input('>>')
                    if msg == 'exit':
                        break
                    if msg == '':
                        continue
                    msg = user_name + ': ' + msg
                    msg = fernet.encrypt(msg.encode())
                    data = json.dumps(
                        {'tag': 'encrypted', 'content': msg.decode()})
                    self.client(data.encode())
            except Exception as e:
                print(e)
        return (1)


if __name__ == '__main__':
    print("Starting client")
    cli = Client()
    cli.start()
