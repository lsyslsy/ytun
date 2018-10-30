import os
import socket
import logging
import struct
import selectors

LISTEN_IP = ""
LISTEN_PORT = 1082

ALLOW_CLIENT_NUM = 1            # max active client num

selector = selectors.DefaultSelector()
class Server:
    def __init__(self):
        self.listen_sock = None
        self.outside_sock = None

        self.wait_outside_queues = []
        self.client_count = 0

    def create_listen_sock(self):
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.bind((LISTEN_IP, LISTEN_PORT))
        self.listen_sock.listen(ALLOW_CLIENT_NUM)


    def close_listen_sock(self):
        self.listen_sock.close()
        

    def run(self):
        self.create_listen_sock()
        while True:
            retv = self.listen_sock.accept()
            if retv is None:
                return
            client_sock, addr = retv
            # 收到客户端的信息，版本和支持method
            data = client_sock.recv(1024)
            if len(data) == 0:
                raise Exception("no data")
            print(data)
            # no authen
            resp = b'\x05\x00'

            client_sock.send(resp)
            req = client_sock.recv(1024)
            if req is None:
                raise Exception('client down')
            #b'\x05\x01\x00\x01s\xef\xd2\x1b\x00P'
            print(req)
            if req[0] != 0x05:
                raise Exception('protocol version error')
            cmd = req[1]
            success = False
            if cmd == 0x01:
                address_type = req[3]
                offset = 3
                if address_type == 1: # ipv4
                    offset += 1
                    data = req[offset:offset+4]
                    addr = socket.inet_ntop(socket.AF_INET, data)
                    offset += 4
                    port = struct.unpack(">H", req[offset:offset+2])[0]

                elif address_type == 3: # domainmae
                    offset += 1
                    length = req[offset]
                    offset += 1
                    addr = req[offset: offset+length].decode(encoding='utf-8')
                    offset += length
                    port = struct.unpack(">H", req[offset:offset+2])[0]
                # elif address_type == 4: # ipv6:
                #     pass
                else:
                    raise Exception('address type not support {}'.format(address_type))

                self.outside_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                logging.error('connect to {}:{}'.format(addr, port))
                self.outside_sock.connect((addr, port))
                resp = bytearray()
                resp += b'\x05\x00\x00\x01'
                addr,port = self.outside_sock.getsockname()
                resp += socket.inet_pton(socket.AF_INET, addr)
                resp += struct.pack('>H', port)
                client_sock.send(resp)
                success = True
            else:
                logging.error('cmd {} not support'.format(cmd))
                return
            if success:
                self.register_to_loop(client_sock, self.outside_sock)
                self.loop()


    def register_to_loop(self, client_sock, outside_sock):
        channel = Channel(self, client_sock, outside_sock)
        client_sock.setblocking(False)
        outside_sock.setblocking(False)
        selector.register(client_sock, selectors.EVENT_READ, channel.client_handler)
        selector.register(outside_sock, selectors.EVENT_READ, channel.outside_handler)
        self.client_count += 1

    def loop(self):
        while self.client_count > 0:
            events = selector.select()
            for key, mask in events:
                callback = key.data
                callback(mask)


class Channel:
    def __init__(self, srv, client_sock, outside_sock):
        self.client_sock = client_sock
        self.outside_sock = outside_sock
        self.stopped = False
        self.srv = srv

    def client_handler(self, mask):
        if mask | selectors.EVENT_READ:
            req = self.client_sock.recv(1024)
            if req:
                print('receive from client {}'.format(req))
                self.outside_sock.send(req)
            else:
                print('client down')
                self.stop()

    def outside_handler(self, mask):
        if mask | selectors.EVENT_READ:
            resp = self.outside_sock.recv(1024)
            if resp:
                self.client_sock.send(resp)
            else:
                print(' up down')
                self.stop()

    def stop(self):
        if self.stopped:
            return
        selector.unregister(self.client_sock)
        selector.unregister(self.outside_sock)
        self.client_sock.close()
        self.outside_sock.close()
        self.stopped = True
        self.srv.client_count -= 1




if __name__ == "__main__":
    # 启动服务

    # 如果收到转发，否则等待
    srv = Server()
    srv.run()
