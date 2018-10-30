import os
import socket
import logging
import struct
import selectors

LISTEN_IP = ""
LISTEN_PORT = 1081

ALLOW_CLIENT_NUM = 1            # max active client num

selector = selectors.DefaultSelector()

REMOTE_IP = "127.0.0.1"
REMOTE_PORT = 1082

class Local:
    def __init__(self):
        self.listen_sock = None
        self.outside_sock = None

    def create_listen_sock(self):
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.bind((LISTEN_IP, LISTEN_PORT))
        self.listen_sock.listen(ALLOW_CLIENT_NUM)


    def close_listen_sock(self):
        self.listen_sock.close()

    def create_remote_conn(self):
        self.outside_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.outside_sock.connect((REMOTE_IP, REMOTE_PORT))
        print('connect create success to {}:{}'.format(REMOTE_IP, REMOTE_PORT))

    def run(self):
        self.create_remote_conn()
        self.create_listen_sock()
        retv = self.listen_sock.accept()
        if retv is None:
            print('accept error')
            return
        client_sock, addr = retv
        self.loop(client_sock, self.outside_sock)


    def loop(self, client_sock, outside_sock):
        channel = Channel(client_sock, outside_sock)
        client_sock.setblocking(False)
        outside_sock.setblocking(False)
        selector.register(client_sock, selectors.EVENT_READ, channel.client_handler)
        selector.register(outside_sock, selectors.EVENT_READ, channel.outside_handler)
        while True:
            events = selector.select()
            for key, mask in events:
                callback = key.data
                callback(mask)


class Channel:
    def __init__(self, client_sock, outside_sock):
        self.client_sock = client_sock
        self.outside_sock = outside_sock
        self.up_queue = []
        self.down_queue = []

    def client_handler(self, mask):
        if mask | selectors.EVENT_READ:
            req = self.client_sock.recv(4096)
            if req:
                print('receive from client {}'.format(req))
                self.outside_sock.send(req)
            else:
                print('client down')
                self.stop()

    def outside_handler(self, mask):
        if mask | selectors.EVENT_READ:
            resp = self.outside_sock.recv(4096)
            if resp:
                self.client_sock.send(resp)
            else:
                print(' up down')
                self.stop()

    def stop(self):
        selector.unregister(self.client_sock)
        selector.unregister(self.outside_sock)
        self.client_sock.close()
        self.outside_sock.close()




if __name__ == "__main__":
    # 启动服务

    # 如果收到转发，否则等待
    srv = Local()
    srv.run()
