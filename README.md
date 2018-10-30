# ytun

A simple proxy program.

## server
run at the remote, connect to the intenet

## local
run at local. process client request, send to remote server, and recv response.

## test
### run without local
suppose server open port at 1082

python3 server.py

curl --socks5 127.0.0.1:1082 http://www.baidu.com/

### run with local
suppose server open port at 1082

suppose local open port at 1081

curl --socks5 127.0.0.1:1081 http://www.baidu.com/
