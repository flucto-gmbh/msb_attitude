from threading import Thread
import zmq


class IMUPoller(Thread):

    def __init__(self, topic : str, config : dict):
        super().__init__()
        self.topic = topic
                #    time, uptime, acc_x, acc_y, acc_z, rot_x, rot_y, rot_z, mag_x, mag_y, mag_z, temp
        self.data = [0] * 12

        # connect to xpub socket from broker here
        # set the context 

        # self.context = 

    def run(self):
        print('start poller {}'.format(self.id))
        subscriber = context.socket(zmq.SUB)
        subscriber.connect("tcp://127.0.0.1:5559")
        subscriber.setsockopt_string(zmq.SUBSCRIBE, self.topic)
        self.loop = True
        while self.loop:
            message = subscriber.recv()
            print('poller {}: {}'.format(self.id, message))

    def stop(self):
        self.loop = False
