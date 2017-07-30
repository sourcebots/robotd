"""Actual device classes."""
from pathlib import Path
from threading import Lock, Thread, Event

import serial

from sb_vision import Camera as VisionCamera, Vision
from robotd import usb
from robotd.devices_base import Board, BoardMeta
from robotd.game_specific import MARKER_SIZES


class MotorBoard(Board):
    """Student Robotics-era Motor board."""

    lookup_keys = {
        'ID_VENDOR': 'Student_Robotics',
        'subsystem': 'tty',
    }

    @classmethod
    def included(cls, node):
        return node['ID_MODEL'] == 'MCV4B'

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
        # set both motors to brake
        self.connection.write(b'\x00\x02\x02\x03\x02')
        self._status = {'m0': 'brake', 'm1': 'brake'}

    def status(self):
        """Brief status description of the peripheral."""
        return self._status

    def _speed_byte(self, value):
        if value == 'coast':
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
            2, self._speed_byte(self._status['m0']),
            3, self._speed_byte(self._status['m1']),
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


class GameState(Board):
    """ State storage for the game, keeps a store of everything it has received """

    # define the name od the board
    board_type_id = 'game'
    create_on_startup = True

    def __init__(self):
        super().__init__({})
        self.state = {'zone': 0, 'mode': 'development'}

    @classmethod
    def name(cls, node):
        return "state"

    def command(self, cmd):
        self.state.update(cmd)

    def status(self):
        return self.state


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
        # We get the bus path to the device inferred from the DEVPATH
        # from systemd.
        path = tuple(int(x) for x in (
            self.node['DEVPATH'].rsplit('-', 1)[-1].split('.')
        ))

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

    # TODO Get the serial from the USB connection so we can handle 2 cameras without an issue
    # ...(This might not even be possible if the cameras are the same model)
    lookup_keys = {
        'subsystem': 'video4linux',
    }

    def __init__(self, node, camera=None, token_sizes=None):
        super().__init__(node)
        # TODO do not hard-code this, detect from which camera is being used
        if camera is None:
            CAM_IMAGE_SIZE = (1280, 720)
            FOCAL_DISTANCE = 720
            camera = VisionCamera(self.node['DEVNAME'], CAM_IMAGE_SIZE, FOCAL_DISTANCE)
        if token_sizes is None:
            self.token_sizes = MARKER_SIZES
        else:
            self.token_sizes = token_sizes
        self.thread = None
        self.vision = self._create_vision(camera)
        self.stop_event = Event()
        self.latest_results = []
        self._status = {'status': 'uninitialised'}

    @staticmethod
    def _create_vision(camera):
        return Vision(camera, MARKER_SIZES)

    @classmethod
    def name(cls, node):
        # Get device name
        return Path(node['DEVNAME']).stem

    def vision_thread(self):
        self.stop_event.clear()
        while not self.stop_event.is_set():
            image = self.vision.snapshot()
            results = self.vision.process_image(image)
            # print("Vision snapshot: ", results)
            self.latest_results = {"tokens": [x.__dict__ for x in results]}
            self.broadcast(self.latest_results)

    def start(self):
        """Open connection to peripheral."""
        self.vision.init()
        self._status = {'status': 'initialised'}
        self.thread = Thread(target=self.vision_thread)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join()

    def status(self):
        """Get latest image results"""
        return {}

    def command(self, cmd):
        """Run user-provided command."""
        pass


class ServoAssembly(Board):
    lookup_keys = {
        'subsystem': 'tty',
        'ID_VENDOR_ID': '1a86',
        'ID_MODEL_ID': '7523',
    }

    NUM_SERVOS = 16

    @classmethod
    def name(cls, node):
        """Board name."""
        return 'SB_{}'.format(node['MINOR'])

    def start(self):
        device = self.node['DEVNAME']
        self.connection = serial.Serial(device, baudrate=115200)
        (self.fw_version,) = self._command('version')
        self._servo_status = {}
        self.make_safe()

    def _command(self, *args):
        line = ' '.join(str(x) for x in args).encode('utf-8') + b'\n'
        self.connection.write(line)
        self.connection.flush()

        results = []

        while True:
            line = self.connection.readline()

            if line.startswith(b'+ '):
                return results
            elif line.startswith(b'- '):
                raise RuntimeError(line[2:].decode('utf-8'))
            elif line.startswith(b'# '):
                continue  # Skip
            elif line.startswith(b'> '):
                results.append(line[2:].decode('utf-8'))
            else:
                raise RuntimeError("wtf is this")

    def make_safe(self):
        for servo in range(NUM_SERVOS):
            self._set_servo(servo, None)

    def _set_servo(self, servo, status):
        if status is None:
            level = 0
        elif 0 <= status <= 1:
            level = 150 + int((550 - 150) * status)
        self._command('servo', servo, level)
        self._servo_status[str(servo)] = status

    def status(self):
        return {
            'servos': self._servo_status,
            'fw-version': self.fw_version,
        }

    def command(self, cmd):
        servos = cmd.get('servos', {})
        for servo_id, status in servos.items():
            self._set_servo(int(servo_id), status)



# Grab the full list of boards from the workings of the metaclass
BOARDS = BoardMeta.BOARDS
