import unittest
import time
import threading
import socket

import json

from robotd.master import MasterProcess


class TestVision(unittest.TestCase):
    def setUp(self):
        self.robotd = MasterProcess('/tmp/')
        self.run = True
        self.thread = threading.Thread(target=self.bg_thread)
        self.thread.start()
        time.sleep(0.5)

    def bg_thread(self):
        while self.run:
            self.robotd.tick()
            time.sleep(1)

    def test_vision_lag(self):
        # We're assuming you have a camera plugged in
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        sock.connect("/tmp/robotd/camera/video0")
        while True:
            response = sock.recv(2048)
            print("i", json.loads(response.decode("utf-8")))

    def tearDown(self):
        self.run = False
        self.robotd.cleanup()


if __name__ == "__main__":
    print("For these tests we assume you have a webcam plugged in.")
    unittest.main()
