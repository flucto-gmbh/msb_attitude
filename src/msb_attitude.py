import zmq
import logging
import sys
from os import path
import time
import numpy as np

# add ahrs directory to PYTHONPATH
SCRIPT_DIR = path.dirname(path.abspath(__file__))
sys.path.append(path.dirname(SCRIPT_DIR))

print(SCRIPT_DIR)

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

try:
    from imu_poller import IMUPoller
except ImportError as e:
    print(f'failed to import IMUPoller: {e}')
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


def main():array

    config = init()

    logging.debug('msb_attitude.py starting up')
    connect_to_sub = f'{config["ipc_protocol"]}:{config["subscriber_ipc_port"]}'
    connect_to_pub = f'{config["ipc_protocol"]}:{config["publisher_ipc_port"]}'

    ctx = zmq.Context()
    # zmq_socket_sub = ctx.socket(zmq.SUB)
    # zmq_socket_pub = ctx.socket(zmq.SUB)
    """
    logging.debug(f'trying to connect to {connect_to_sub}')
    try:
        zmq_socket_sub.connect(connect_to_sub)
    except Exception as e:
        logging.fatal(f'failed to bind to zeromq socket {connect_to_sub}: {e}')
        sys.exit(-1)

    zmq_socket_sub.setsockopt(zmq.SUBSCRIBE, IMU_TOPIC)
    logging.debug(f'successfully connected to broker xpub socket as subscriber')
    """

    logging.debug(f'trying to connect to {connect_to_pub}')
    try:
        zmq_socket_pub.connect(connect_to_pub)
    except Exception as e:
        logging.fatal(f'failed to connect to socket {connect_to_pub}: {e}')
        sys.exit(-1)

    logging.debug(f'successfully connected to broker xsub socket as publisher')

    imu_poller = IMUPoller('imu', config, ctx)
    logging.debug('starting IMU poller')
    imu_poller.start()
    logging.debug('successfully started IMU poller')

    q_current = Quaternion(np.array([1, 1, 1, 1]))
    q_old = Quaternion(np.array([1, 1, 1, 1]))

    cfilter = Complementary(frequency=config['sample_rate'], q0 = q_current)
    logging.debug(f'entering endless loop')

    while True:
        if imu_poller.new_data:
            
            # get data from poller
            data = np.array(imu_poller.get_data())

            # print received data if --print flag was set
            if config['print']:
                print(f'Imu: {data}')

            # update filter and store the updated orientation
            q_current = Quaternion(
                cfilter.update(
                    q_old.A,
                    data[5:8],    #gyr
                    data[2:5],    #acc
                    data[8:11]    #mag
                )
            )

            if config['print']:
                print(f'Orientation: {q_current}')

            # save for next step
            q_old = q_current
            
            # push to XSUB msb_broker to publish data

            
        else:
            time.sleep(0.001)

        # recv = zmq_socket_sub.recv_pyobj()
        # [topic, data] = zmq_socket_sub.recv_multipart()
        # topic = topic.decode('utf-8')

        # if config['print']: 
        #     print(f'{pickle.loads(data)}')
       
if __name__ == '__main__':
    main()
