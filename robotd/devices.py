"""Actual device classes."""
import json
from threading import Lock, Thread

import serial

from robotd import usb
from robotd.devices_base import Board, BoardMeta
from robotd.vision.camera import Camera as VisionCamera
from robotd.vision.vision import Vision


class MotorBoard(Board):
    """Student Robotics-era Motor board."""

    lookup_keys = {
        'ID_VENDOR': 'Student_Robotics',
        'subsystem': 'tty',
    }

    @classmethod
    def included(cls, node):
        return node['ID_MODEL'] == 'MCV3B'

    @classmethod
    def name(cls, node):
        """Board name - actually fetched over serial."""
        return node['ID_SERIAL_SHORT']

    def start(self):
        """Open connection to peripheral."""
        device = self.node['DEVNAME']
        self.connection = serial.Serial(device, baudrate=1000000)
        self.make_safe()

    def make_safe(self):
        """
        Set peripheral to a safe state.

        This is called after control connections have died.
        """
        # Brake both the motors
        self.connection.write(b'\x00\x02\x02\x03\x02')
        self._status = {'left': 'brake', 'right': 'brake'}

    def status(self):
        """Brief status description of the peripheral."""
        return self._status

    def _speed_byte(self, value):
        if value == 'free':
            return 1
        elif value == 'brake':
            return 2
        elif -1 <= value <= 1:
            return 128 + int(100 * value)
        else:
            raise ValueError("Non-understood speed")

    def command(self, cmd):
        """Run user-provided command."""
        self._status.update(cmd)
        self.connection.write(bytes([
            2, 2,
            3, 2,
            2, 1,
            3, 1,
            2, self._speed_byte(self._status['left']),
            3, self._speed_byte(self._status['right']),
        ]))


class BrainTemperatureSensor(Board):
    """
    Internal Raspberry Pi temperature sensor.

    This has extremely limited practical use and is basically here to serve as
    an example of how to add new devices.
    """

    lookup_keys = {
        'subsystem': 'thermal',
    }

    enabled = False

    @classmethod
    def name(cls, node):
        """Simple node name."""
        return node.sys_name

    def status(self):
        """Brief status description of the peripheral."""
        with open('{}/temp'.format(self.node.sys_path), 'r') as f:
            temp_milli_degrees = int(f.read())
        return {'temperature': temp_milli_degrees / 1000}


class PowerBoard(Board):
    lookup_keys = {
        'subsystem': 'usb',
        'ID_VENDOR': 'Student_Robotics',
    }

    @classmethod
    def included(cls, node):
        return node['ID_MODEL'] == 'Power_board_v4'

    @classmethod
    def name(cls, node):
        """Board name."""
        return node['ID_SERIAL_SHORT']

    def start(self):
        """Open connection to peripheral."""
        path = tuple(int(x) for x in self.node['DEVNAME'].split('/')[4:])

        for device in usb.enumerate():
            if device.path == path:
                self.device = device
                break
        else:
            raise RuntimeError("Cannot open USB device by path")

        self.device.open()
        self.make_safe()

    def _set_power_outputs(self, level):
        for command in (0, 1, 2, 3, 4, 5):
            self.device.control_write(
                64,
                level,
                command,
            )

    def make_safe(self):
        self._set_power_outputs(0)

    def status(self):
        return {}

    def command(self, cmd):
        if 'power' in cmd:
            power = bool(cmd['power'])
            self._set_power_outputs(1 if power else 0)


class Camera(Board):
    """Camera"""

    lookup_keys = {
        'subsystem': 'video4linux',
    }

    def __init__(self, node):
        super().__init__(node)
        # TODO do not hardcode this, detect which camera is being used
        CAM_IMAGE_SIZE = (1280, 720)
        FOCAL_DISTANCE = 720
        self.camera = VisionCamera(self.node['DEVNAME'], CAM_IMAGE_SIZE, FOCAL_DISTANCE)
        self.vision = Vision(self.camera, token_size=(0.1, 0.1))  # TODO do not hardcode the token size
        self.thread = None
        self.vision_lock = Lock()
        self.latest_results = []
        self._status = {'status': 'uninitialised'}

    @classmethod
    def name(cls, node):
        # Get device name
        return node['DEVNAME'].split('/')[-1]

    def vision_thread(self):
        while True:
            results = self.vision.snapshot()
            print("Vision snapshot: ", results[0])
            with self.vision_lock:
                self.latest_results, _ = results


    def start(self):
        """Open connection to peripheral."""
        self.vision.init()
        self._status = {'status': 'initialised'}
        self.thread = Thread(target=self.vision_thread)
        self.thread.start()

    def status(self):
        """Brief status description of the peripheral."""
        with self.vision_lock:
            results = self.latest_results
        return json.dumps(results, default=lambda x: x.__dict__)

    def command(self, cmd):
        """Run user-provided command."""
        pass


# Grab the full list of boards from the workings of the metaclass
BOARDS = BoardMeta.BOARDS


class Encoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__
