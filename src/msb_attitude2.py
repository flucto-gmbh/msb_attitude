import zmq
import logging
import sys
from os import path
import pickle
import numpy as np
import time
import threading
from collections import deque


try:
    from attitude_config import (init, ATTITUDE_TOPIC, IMU_TOPIC)
except ImportError as e:
    print(f'failed to import: {e} - exit')
    sys.exit(-1)

imu_buffer = deque(maxlen=1)

def read_from_zeromq(socket):
    logging.debug(f'in consumer thread')
    global imu_buffer
    try:
        while True:
            topic_bin, data_bin = socket.recv_multipart()
            logging.debug(f'received {topic_bin}')
            imu_buffer.append(data_bin)

    except Exception as e:
        logging.critical(f"failed: {e}")
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

    logging.debug(f'starting imu consumer thread')
    threading.Thread(target=read_from_zeromq, daemon=True, args=[socket_broker_xpub]).start()

    t_old = time.time()
    t_cur = time.time()
    delta_t = 0

    try:
        while True:

            # get data from socket
            t_cur = time.time()
            delta_t = t_cur - t_old

            if len(imu_buffer) == 0:
                logging.warning(f'no imu data in buffer, sleeping')
                time.sleep(0.1)
                continue
            

            data = pickle.loads(
                imu_buffer.pop()
            )

            imu_time = data[0]
            acc = data[2:5]
            gyr = data[5:8]
            mag = data[8:11]

            if config['print']:
                print(f'time : {imu_time} acc : {acc} gyr : {gyr} mag : {mag}')
                print(f'delta_t : {delta_t}')

            # print received data if --print flag was set
            # if config['print']:
            #     print(f'imu: {data}')

            # save for next step
            socket_broker_xsub.send_multipart(
                [
                    ATTITUDE_TOPIC,    # topic
                    pickle.dumps( # serialize the payload
                        [0.1, 0.2, 0.3, 0.4]
                    )
                ]
            )
            while (tt := time.time() - t_old) < 0.1:
                print(f'sleeping {tt}')
                time.sleep(0.001)

            t_old = t_cur

    except Exception as e:
        logging.fatal(f'received Exception: {e}')
        logging.fatal('cleaning up')

        socket_broker_xpub.close()
        socket_broker_xsub.close()
        ctx.terminate()

       
if __name__ == '__main__':
    main()
