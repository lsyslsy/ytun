import os
import socket
import logging
import struct
import selectors
import threading
import log_config

LISTEN_IP = ""
LISTEN_PORT = 1082

ALLOW_CLIENT_NUM = 1            # max active client num

class Server:
    def __init__(self):
        self.listen_sock = None

        self.wait_outside_queues = []

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
                logging.info("accept no data")
                client_sock.close()
                continue
            print(data)
            # no authen
            resp = b'\x05\x00'

            client_sock.send(resp)
            req = client_sock.recv(1024)
            if not req:
                logging.info('client down')
                client_sock.close()
                continue
            #b'\x05\x01\x00\x01s\xef\xd2\x1b\x00P'
            print(req)
            if req[0] != 0x05:
                raise Exception('protocol version error')
            cmd = req[1]
            success = False
            outside_sock = None
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

                outside_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                logging.error('connect to {}:{}'.format(addr, port))
                outside_sock.connect((addr, port))
                resp = bytearray()
                resp += b'\x05\x00\x00\x01'
                addr,port = outside_sock.getsockname()
                resp += socket.inet_pton(socket.AF_INET, addr)
                resp += struct.pack('>H', port)
                client_sock.send(resp)
                success = True
            else:
                logging.error('cmd {} not support'.format(cmd))
                return
            if success:
                channel = Channel(client_sock, outside_sock)
                channel_thread = threading.Thread(target=channel.run)
                channel_thread.start()
                print('---------{}active count'.format(threading.active_count()))
        self.close_listen_sock()




class Channel:
    def __init__(self, client_sock, outside_sock):
        self.client_sock = client_sock
        self.outside_sock = outside_sock
        self.stopped = False
        self.selector = selectors.DefaultSelector()

    def client_handler(self, mask):
        if mask | selectors.EVENT_READ:
            try:
                req = self.client_sock.recv(4096)
                if req:
                    print('receive from client {}'.format(req))
                    self.outside_sock.send(req)
                else:
                    print('client down')
                    self.stop()
            except socket.error as e:
                print('client down {}'.format(e))
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
        if self.stopped:
            return
        self.selector.unregister(self.client_sock)
        self.selector.unregister(self.outside_sock)
        self.client_sock.close()
        self.outside_sock.close()
        self.stopped = True

    def register_to_loop(self):
        self.client_sock.setblocking(False)
        self.outside_sock.setblocking(False)
        self.selector.register(self.client_sock, selectors.EVENT_READ, self.client_handler)
        self.selector.register(self.outside_sock, selectors.EVENT_READ, self.outside_handler)

    def loop(self):
        while not self.stopped:
            events = self.selector.select()
            for key, mask in events:
                callback = key.data
                callback(mask)

    def run(self):
        self.register_to_loop()
        self.loop()
        print('thread down')



if __name__ == "__main__":
    # 启动服务

    log_config.set_log('server')
    # 如果收到转发，否则等待
    srv = Server()
    srv.run()
