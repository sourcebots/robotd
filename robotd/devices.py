import serial

from robotd.devices_base import Board, BoardMeta


class MotorBoard(Board):
    lookup_keys = {
        'ID_MODEL': 'MCV3B',
        'ID_VENDOR': 'Student_Robotics',
        'subsystem': 'tty',
    }

    @classmethod
    def name(cls, node):
        return node['ID_SERIAL_SHORT']

    def start(self):
        device = self.node['DEVNAME']
        self.connection = serial.Serial(device, baudrate=1000000)
        self.make_safe()

    def make_safe(self):
        # Brake both the motors
        self.connection.write(b'\x00\x01\x02\x02\x02')
        self._status = {'left': 'brake', 'right': 'brake'}

    def status(self):
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
        tx_buffer = bytearray()

        if 'left' in cmd:
            tx_buffer.append(2)
            tx_buffer.append(self._speed_byte(cmd['left']))

        if 'right' in cmd:
            tx_buffer.append(2)
            tx_buffer.append(self._speed_byte(cmd['right']))

        self._status.update(cmd)

        if not tx_buffer:
            return

        self.connection.write(tx_buffer)


class BrainTemperatureSensor(Board):
    lookup_keys = {
        'subsystem': 'thermal',
    }

    @classmethod
    def name(cls, node):
        return node.sys_name

    def status(self):
        with open('{}/temp'.format(self.node.sys_path), 'r') as f:
            temp_milli_degrees = int(f.read())
        return {'temperature': temp_milli_degrees / 1000}


BOARDS = BoardMeta.BOARDS
