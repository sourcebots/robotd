"""Actual device classes."""

import os
import random
import struct
import subprocess

import serial

from . import usb
from .devices_base import Board, BoardMeta

try:
    # See if we have vision support
    import sb_vision  # noqa: F401
    ENABLE_VISION = True
except ImportError:
    print("WARNING: sb_vision not installed, disabling vision support")
    ENABLE_VISION = False

if ENABLE_VISION:
    # Register the camera 'board' by importing it
    from .camera import Camera  # noqa: F401


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

    @classmethod
    def byte_for_speed(cls, value):
        """
        Get the byte value for the given speed value.

        Accepts float or a string of 'coast' or 'brake'.
        """

        if value == 'coast':
            return 1
        elif value == 'brake':
            return 2
        elif -1 <= value <= 1:
            return 128 + int(100 * value)
        else:
            raise ValueError('Unknown speed value: {}'.format(value))

    def command(self, cmd):
        """Run user-provided command."""
        self._status.update(cmd)
        self.connection.write(bytes([
            2, 2,
            3, 2,
            2, 1,
            3, 1,
            2, self.byte_for_speed(self._status['m0']),
            3, self.byte_for_speed(self._status['m1']),
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

    def read_temperature_value(self):
        path = '{}/temp'.format(self.node.sys_path)
        with open(path) as file:
            return int(file.read())

    def status(self):
        """Brief status description of the peripheral."""
        temp_milli_degrees = self.read_temperature_value()
        return {'temperature': temp_milli_degrees / 1000}


class GameState(Board):
    """
    State storage for the game, keeps a store of everything it has received.
    """

    # define the name od the board
    board_type_id = 'game'
    create_on_startup = True

    def __init__(self):
        super().__init__({})
        self.state = {'zone': 0, 'mode': 'development'}

    @classmethod
    def name(cls, node):
        return 'state'

    def command(self, cmd):
        self.state.update(cmd)

    def status(self):
        return self.state


class PowerBoard(Board):
    """A power board."""

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

        for device in usb.enumerate_devices():
            if device.path == path:
                self.device = device
                break
        else:
            raise RuntimeError('Cannot open USB device by path')

        self.device.open()
        self.make_safe()

        # This power board is now ready; signal to systemd that robotd is
        # therefore ready
        subprocess.check_call([
            'systemd-notify',
            '--ready',
            '--pid={}'.format(os.getppid()),
        ])

    def _set_power_outputs(self, level):
        for command in (0, 1, 2, 3, 4, 5):
            self.device.control_write(
                64,
                level,
                command,
            )

    def _set_start_led(self, value):
        self.device.control_write(64, value, 6)

    def _buzz_piezo(self, args):
        data = struct.pack("HH", args['frequency'], args['duration'])
        self.device.control_write(64, 0, 8, data)

    @property
    def start_button_status(self):
        result = self.device.control_read(64, 0, 8, 4)
        return any(result)

    def make_safe(self):
        self._set_power_outputs(0)

    def status(self):
        return {'start-button': self.start_button_status}

    def command(self, cmd):
        if 'power' in cmd:
            power = bool(cmd['power'])
            self._set_power_outputs(1 if power else 0)
        elif 'start-led' in cmd:
            value = bool(cmd['start-led'])
            self._set_start_led(1 if value else 0)
        elif 'buzz' in cmd:
            self._buzz_piezo(cmd['buzz'])


class ServoAssembly(Board):
    """
    A servo assembly.

    Technically this is actually an arduino with a servo shield attached.
    """

    lookup_keys = {
        'subsystem': 'tty',
    }

    NUM_SERVOS = 16
    GPIO_IDS = range(2, 13)

    INPUT = 'hi-z'

    @classmethod
    def included(cls, node):
        if 'ID_MODEL_ID' not in node or 'ID_VENDOR_ID' not in node:
            return False

        return (node['ID_MODEL_ID'], node['ID_VENDOR_ID']) in [
            ('0043', '2a03'),  # Fake Uno
            ('7523', '1a86'),  # Real Uno
        ]

    @classmethod
    def name(cls, node):
        """Board name."""
        return node.get('ID_SERIAL_SHORT',
                        'SB_{}'.format(node['MINOR']))

    def start(self):
        device = self.node['DEVNAME']

        self.connection = serial.Serial(device, baudrate=9600, timeout=0.2)

        if hasattr(self.connection, 'reset_input_buffer'):
            self._reset_input_buffer = self.connection.reset_input_buffer
        else:
            self._reset_input_buffer = self.connection.flushInput

        (self.fw_version,) = self._command('version')
        self.fw_version = self.fw_version.strip()
        self._servo_status = {}
        self._pin_status = {}
        self._pin_values = {}
        self._analogue_values = {}
        self._ultrasound_value = None

        self.make_safe()
        print('Finished initialising servo assembly on {}'.format(device))

    def _command(self, *args):
        command_id = random.randint(1, 65535)

        while True:
            self._reset_input_buffer()

            command_id_part = '@{id} '.format(id=command_id).encode('utf-8')
            command_args_part = ' '.join(str(x) for x in args).encode('utf-8')

            line = command_id_part + command_args_part + b'\n'
            self.connection.write(b'\0')
            self.connection.write(line)
            self.connection.flush()

            print('Sending to servo assembly:', line)

            comments = []
            results = []

            while True:
                line = self.connection.readline()

                print('Got back from servo:', line)

                if not line:
                    # Leave the loop and reissue the command
                    break

                if line.startswith(b'@'):
                    returned_command_id_str, line = line[1:].split(b' ', 1)
                    returned_command_id = int(
                        returned_command_id_str.decode('utf-8'),
                    ) & 0xffff

                    if returned_command_id != command_id:
                        print(
                            'Got response for different command, ignoring...',
                        )
                        continue

                try:
                    if line.startswith(b'+ '):
                        return results
                    elif line.startswith(b'- '):
                        if b'unknown command' in line:
                            break  # try again
                        else:
                            raise RuntimeError(
                                line[2:].decode('utf-8') +
                                '\n' +
                                '\n'.join(comments),
                            )
                    elif line.startswith(b'# '):
                        comments.append(line[2:].decode('utf-8').strip())
                    elif line.startswith(b'> '):
                        results.append(line[2:].decode('utf-8').strip())
                    else:
                        raise ValueError('wtf is this')
                except ValueError:
                    break

    def make_safe(self):
        for servo in range(self.NUM_SERVOS):
            self._set_servo(servo, None)
        for pin in self.GPIO_IDS:
            self._write_pin(pin, self.INPUT)

    def _set_servo(self, servo, status):
        if status is None:
            level = 0
        elif -1 <= status <= 1:
            # Adjust to be in the range 0-1
            status_unit = (status + 1) / 2
            level = 150 + int((550 - 150) * status_unit)
        else:
            return

        self._command('servo', servo, level)
        self._servo_status[str(servo)] = level

    def _write_pin(self, pin, setting):
        self._pin_status[pin] = setting
        return self._command('gpio-write', pin, setting)

    def _read_pin(self, pin):
        result = self._command('gpio-read', pin)[0]
        self._pin_values.update({pin: result})

    def _read_analogue(self):
        results = self._command('analogue-read')
        for result in results:
            name, value = result.split(' ')
            self._analogue_values.update({name: value})

    def _read_ultrasound(self, trigger_pin, echo_pin):
        found_values = []

        for i in range(3):
            result = self._command('ultrasound-read', trigger_pin, echo_pin)[0]
            found_values.append(float(result))

        self._ultrasound_value = list(sorted(found_values))[1] / 1000.0

    def status(self):
        return {
            'servos': self._servo_status,
            'pins': self._pin_status,
            'pin-values': self._pin_values,
            'fw-version': self.fw_version,
            'analogue-values': self._analogue_values,
            'ultrasound': self._ultrasound_value,
        }

    def command(self, cmd):
        # handle servos
        servos = cmd.get('servos', {})
        for servo_id, status in servos.items():
            self._set_servo(int(servo_id), status)

        # handle writing pins
        pins = cmd.get('pins', {})
        for pin, status in pins.items():
            self._write_pin(int(pin), status)

        # handle reading pins
        self._pin_values = {}

        pins = cmd.get('read-pins', [])
        for pin in pins:
            self._read_pin(int(pin))

        # handle reading analogue pins
        self._analogue_values = {}

        read_analogue = cmd.get('read-analogue', False)
        if read_analogue:
            self._read_analogue()

        # handle ultrasound
        self._ultrasound_value = None

        read_ultrasound = cmd.get('read-ultrasound', [])
        if len(read_ultrasound) == 2:
            self._read_ultrasound(read_ultrasound[0], read_ultrasound[1])


# Grab the full list of boards from the workings of the metaclass
BOARDS = BoardMeta.BOARDS
