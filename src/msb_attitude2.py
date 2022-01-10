import zmq
import logging
import sys
from os import path
import pickle
import numpy as np
from time import time

# add ahrs directory to PYTHONPATH
SCRIPT_DIR = path.dirname(path.abspath(__file__))
sys.path.append(path.dirname(SCRIPT_DIR))

try:
    from ahrs.ahrs.filters import (Complementary, FAMC)
except ImportError as e:
    print(f'failed to import Complementary filter from ahrs: {e}')
    sys.exit(-1)

try:
    from ahrs.ahrs.common import Quaternion
except ImportError as e:
    print(f'failed to import Quaternion from ahrs: {e}')
    sys.exit(-1)

try:
    from attitude_config import (init, ATTITUDE_TOPIC, IMU_TOPIC)
except ImportError as e:
    print(f'failed to import: {e} - exit')
    sys.exit(-1)


def main():

    config = init()

    logging.debug('msb_attitude.py starting up')
    
    broker_xsub = f'{config["ipc_protocol"]}:{config["broker_xsub"]}'
    broker_xpub = f'{config["ipc_protocol"]}:{config["broker_xpub"]}'

    ctx = zmq.Context()
    socket_broker_xsub = ctx.socket(zmq.PUB)
    logging.debug(f'trying to connect to {broker_xsub}')
    try:
        socket_broker_xsub.connect(broker_xsub)
    except Exception as e:
        logging.fatal(f'failed to bind to zeromq socket {broker_xsub}: {e}')
        sys.exit(-1)
    logging.debug(f'successfully connected to broker XSUB socket as a publisher')

    socket_broker_xpub = ctx.socket(zmq.SUB)
    logging.debug(f'trying to connect to {broker_xpub}')
    try:
        socket_broker_xpub.connect(broker_xpub)
    except Exception as e:
        logging.fatal(f'failed to bind to zeromq socket {broker_xpub}: {e}')
        sys.exit(-1)
    logging.debug(f'successfully connected to broker XPUB socket as a subscriber')

    socket_broker_xpub.setsockopt(zmq.SUBSCRIBE, IMU_TOPIC)
    
    logging.debug('creating quaternions for attitude estimation')
    q_current = Quaternion(np.array([1, 1, 1, 1]))
    q_old = Quaternion(np.array([1, 1, 1, 1]))
    
    logging.debug('instantiating complementary filter object')
    cfilter = Complementary(frequency=config['sample_rate'], q0 = q_current)
    logging.debug(f'entering endless loop')

    try:
        while True:

            # get data from socket
            [topic, data] = socket_broker_xpub.recv_multipart()
            topic = topic.decode('utf-8')
            data = pickle.loads(data)

            time = data[0]
            acc = data[2:5]
            gyr = data[5:8]
            mag = data[8:11]

            if config['print']:
                print(f'{topic} : {data}')
                print(f'    acc : {acc} gyr : {gyr} mag : {mag}')

            # print received data if --print flag was set
            # if config['print']:
            #     print(f'imu: {data}')

            # update filter and store the updated orientation
            q_current = Quaternion(
               cfilter.update(
                   q_old.A,
                   gyr,    #gyr
                   acc,    #acc
                   mag    #mag
               )
            )

            if config['print']:
                 print(f'attitude: {q_current}')
    
            # save for next step
            q_old = q_current
            socket_broker_xsub.send_multipart(
                [
                     ATTITUDE_TOPIC,    # topic
                     pickle.dumps( # serialize the payload
                         q_current.A.tolist()
                     )
                ]
            )

    except Exception as e:
        logging.fatal(f'received Exception: {e}')
        logging.fatal('cleaning up')

        socket_broker_xpub.close()
        socket_broker_xsub.close()
        ctx.close()

       
if __name__ == '__main__':
    main()
