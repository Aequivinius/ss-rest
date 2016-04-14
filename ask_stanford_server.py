import socket
import argparse , sys

HOSTNAME = 'localhost'
PORT = 2020

def setup(host,port):
	s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	s.connect((host,port))
	return s
	
def send(socket_,message):
	if not isinstance(message, bytes):
		try:
			message = message.encode()
		except Exception as e:
			print(e)
			return
			
	socket_.sendall(message)
	socket_.shutdown(socket.SHUT_WR)
	
def get_reply(socket_,expected=1024):
	reply = ""
	while True:
		data = socket_.recv(expected)
		if data == b'':
			break
		reply += data.decode()
	
	return reply.strip()

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('message',action="store")
	arguments = parser.parse_args(sys.argv[1:])
	
	s = setup(HOSTNAME,PORT)
	send(s,arguments.message)
	r = get_reply(s)
	print(r)
	