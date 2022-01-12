import zmq
import logging
import sys
from os import path
import pickle
import numpy as np
import time

"""

import numpy as np
from scipy.signal import filtfilt, butter
from quaternion import quaternion, from_rotation_vector, rotate_vectors


def estimate_orientation(a, w, t, alpha=0.9, g_ref=(0., 0., 1.),
                         theta_min=1e-6, highpass=.01, lowpass=.05):
    Estimate orientation with a complementary filter.
    Fuse linear acceleration and angular velocity measurements to obtain an
    estimate of orientation using a complementary filter as described in
    `Wetzstein 2017: 3-DOF Orientation Tracking with IMUs`_
    .. _Wetzstein 2017: 3-DOF Orientation Tracking with IMUs:
    https://pdfs.semanticscholar.org/5568/e2100cab0b573599accd2c77debd05ccf3b1.pdf
    Parameters
    ----------
    a : array-like, shape (N, 3)
        Acceleration measurements (in arbitrary units).
    w : array-like, shape (N, 3)
        Angular velocity measurements (in rad/s).
    t : array-like, shape (N,)
        Timestamps of the measurements (in s).
    alpha : float, default 0.9
        Weight of the angular velocity measurements in the estimate.
    g_ref : tuple, len 3, default (0., 0., 1.)
        Unit vector denoting direction of gravity.
    theta_min : float, default 1e-6
        Minimal angular velocity after filtering. Values smaller than this
        will be considered noise and are not used for the estimate.
    highpass : float, default .01
        Cutoff frequency of the high-pass filter for the angular velocity as
        fraction of Nyquist frequency.
    lowpass : float, default .05
        Cutoff frequency of the low-pass filter for the linear acceleration as
        fraction of Nyquist frequency.
    Returns
    -------
    q : array of quaternions, shape (N,)
        The estimated orientation for each measurement.

    # initialize some things
    N = len(t)
    dt = np.diff(t)
    g_ref = np.array(g_ref)
    q = np.ones(N, dtype=quaternion)

    # get high-passed angular velocity
    w = filtfilt(*butter(5, highpass, btype='high'), w, axis=0)
    w[np.linalg.norm(w, axis=1) < theta_min] = 0
    q_delta = from_rotation_vector(w[1:] * dt[:, None])

    # get low-passed linear acceleration
    a = filtfilt(*butter(5, lowpass, btype='low'), a, axis=0)

    for i in range(1, N):

        # get rotation estimate from gyroscope
        q_w = q[i - 1] * q_delta[i - 1]

        # get rotation estimate from accelerometer
        v_world = rotate_vectors(q_w, a[i])
        n = np.cross(v_world, g_ref)
        phi = np.arccos(np.dot(v_world / np.linalg.norm(v_world), g_ref))
        q_a = from_rotation_vector(
            (1 - alpha) * phi * n[None, :] / np.linalg.norm(n))[0]

        # fuse both estimates
        q[i] = q_a * q_w

    return q
"""


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

    t_old = time.time()
    t_cur = time.time()
    delta_t = 0

    try:
        while True:

            # get data from socket
            t_cur = time.time()
            delta_t = t_cur - t_old
            [topic, data] = socket_broker_xpub.recv_multipart()
            topic = topic.decode('utf-8')
            data = pickle.loads(data)

            imu_time = data[0]
            acc = np.array(data[2:5])
            gyr = np.array(data[5:8])
            mag = np.array(data[8:11])

            if config['print']:
                print(f'{topic} : {data}')
                print(f'time : {imu_time} acc : {acc} gyr : {gyr} mag : {mag}')
                print(f'delta_t : {delta_t}')

            # print received data if --print flag was set
            # if config['print']:
            #     print(f'imu: {data}')

            # update filter and store the updated orientation
            if config['print']:
                 print(f'attitude: {q_current}')
    
            # save for next step
            socket_broker_xsub.send_multipart(
                [
                    ATTITUDE_TOPIC,    # topic
                    pickle.dumps( # serialize the payload
                        [0.1, 0.2, 0.3, 0.4]
                    )
                ]
            )
            while time.time() - t_old < 0.1:
                print('sleeping')
                time.sleep(0.005)
            t_old = t_cur

    except Exception as e:
        logging.fatal(f'received Exception: {e}')
        logging.fatal('cleaning up')

        socket_broker_xpub.close()
        socket_broker_xsub.close()
        ctx.terminate()

       
if __name__ == '__main__':
    main()
