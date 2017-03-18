from robotd.native import _usb
import atexit

context = _usb.ffi.new('struct libusb_context**')
_usb.lib.libusb_init(context)
atexit.register(_usb.lib.libusb_exit, context[0])


class Device(object):
    def __init__(self, device_list, index):
        self._device_list = device_list
        self._index = index
        self._device = self._device_list[0][index]
        self._handle = None

        self._describe()

    def _describe(self):
        port_path = _usb.ffi.new('uint8_t[8]')
        port_length = _usb.lib.libusb_get_port_numbers(
            self._device,
            port_path,
            len(port_path),
        )

        self.path = tuple(port_path[i] for i in range(port_length))

        descriptor = _usb.ffi.new('struct libusb_device_descriptor*')
        _usb.lib.libusb_get_device_descriptor(self._device, descriptor)

        self.vendor = descriptor.idVendor
        self.product = descriptor.idProduct

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def open(self):
        if self._handle is not None:
            return  # Idempotent

        self._handle = _usb.ffi.new('struct libusb_device_handle**')
        _usb.lib.libusb_open(self._device, self._handle)

        if self._handle[0] == _usb.ffi.NULL:
            self._handle = None
            raise RuntimeError("Could not open device")

    def close(self):
        if self._handle is None:
            return  # Idempotent

        _usb.lib.libusb_close(self._handle[0])
        self._handle = None

    def _get_handle(self):
        if self._handle is None:
            raise RuntimeError("Device is not open")

        return self._handle[0]

    def control_write(self, request, value, index, data=None, timeout=3000):
        _usb.lib.libusb_control_transfer(
            self._get_handle(),
            0x00,
            request,
            value,
            index,
            data if data is not None else _usb.ffi.NULL,
            len(data) if data is not None else 0,
            timeout,
        )

    def control_read(self, request, value, index, length, timeout=3000):
        target = _usb.ffi.new('uint8_t[{len}]'.format(len=length))

        size = _usb.lib.libusb_control_transfer(
            self._get_handle(),
            0x80,
            request,
            value,
            index,
            target,
            len(target),
            timeout,
        )

        return bytes(target)[:size]


def enumerate():
    devs = _usb.ffi.new('struct libusb_device***')
    num_devs = _usb.lib.libusb_get_device_list(context[0], devs)

    return [
        Device(devs, i)
        for i in range(num_devs)
    ]
