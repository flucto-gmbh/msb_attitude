import zmq
import logging
import socket
import json
import sys

try:
    from config import init
except ImportError as e:
    logging.error(f'failed to import: {e} - exit')
    sys.exit(-1)

def main():

    config = init()

    logging.debug('msb_attitude.py starting up')
    receiver = f'tcp://127.0.0.1:5556'

    ctx = zmq.Context()
    zmq_socket_receiver = ctx.socket(zmq.SUB)

    logging.debug(f'trying to bind zmq to {receiver}')
    try:
        zmq_socket_receiver.connect(receiver)
    except Exception as e:
        logging.fatal(f'failed to bind to zeromq socket: {e}')
        sys.exit(-1)

    zmq_socket_receiver.setsockopt(zmq.SUBSCRIBE, b'')
    logging.debug(f'successfully bound to fusionlog zeroMQ socket as subscriber')
    logging.debug(f'entering endless loop')

    while True:

        recv = zmq_socket_receiver.recv_pyobj()

        if config['print']: 
            print(f'{recv}')
       
if __name__ == '__main__':
    main()
