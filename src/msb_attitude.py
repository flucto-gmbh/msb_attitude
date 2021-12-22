import zmq
import logging
import sys
import pickle

try:
    from .ahrs.ahrs.filters import (Complementary, FAMC)
except ImportError as e:
    print(f'failed to import Complementary filter from ahrs: {e}')
    sys.exit(-1)

try:
    from .ahrs.ahrs.common import Quaternion
except ImportError as e:
    print(f'failed to import Quaternion from ahrs: {e}')
    sys.exit(-1)

try:
    from attitude_config import (init, ATTITUDE_TOPIC, IMU_TOPIC)
except ImportError as e:
    logging.error(f'failed to import: {e} - exit')
    sys.exit(-1)

def initial_attitude_estimation(tries=5) -> Quaternion: 

    # for as many tries:
    #     find the current (steady state) orientation
    # if not steady_state:
    #     ???
    # returns the initial orientation as a quaternion
    # can we use magnetic field and accelerometer data to
    # estimate the initial orientation? e.g. davenport's q-method
    # or FAMC

    pass


def main():

    config = init()

    logging.debug('msb_attitude.py starting up')
    connect_to_sub = f'{config["ipc_protocol"]}:{config["subscriber_ipc_port"]}'
    connect_to_pub = f'{config["ipc_protocol"]}:{config["publisher_ipc_port"]}'

    ctx = zmq.Context()
    zmq_socket_sub = ctx.socket(zmq.SUB)
    zmq_socket_pub = ctx.socket(zmq.PUB)

    logging.debug(f'trying to connect to {connect_to_sub}')
    try:
        zmq_socket_sub.connect(connect_to_sub)
    except Exception as e:
        logging.fatal(f'failed to bind to zeromq socket {connect_to_sub}: {e}')
        sys.exit(-1)

    zmq_socket_sub.setsockopt(zmq.SUBSCRIBE, IMU_TOPIC)
    logging.debug(f'successfully connected to broker xpub socket as subscriber')

    logging.debug(f'trying to connect to {connect_to_pub}')
    try:
        zmq_socket_pub.connect(connect_to_pub)
    except Exception as e:
        logging.fatal(f'failed to connect to socket {connect_to_pub}: {e}')
        sys.exit(-1)

    logging.debug(f'successfully connected to broker xsub socket as publisher')

    cfilter = Complementary(frequency=config['sample_rate'])

    logging.debug(f'entering endless loop')

    # build a generator classes using threads
    while True:

        #recv = zmq_socket_sub.recv_pyobj()
        [topic, data] = zmq_socket_sub.recv_multipart()
        topic = topic.decode('utf-8')

        if config['print']: 
            print(f'{pickle.loads(data)}')
       
if __name__ == '__main__':
    main()
