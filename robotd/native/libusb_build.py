import cffi

ffibuilder = cffi.FFI()

ffibuilder.set_source("robotd.native._usb", """
    #include <libusb.h>
""", libraries=('usb-1.0',), include_dirs=(
    '/usr/local/include/libusb-1.0',
    '/usr/include/libusb-1.0',
), library_dirs=(
    '/lib/arm-linux-gnueabihf',
))

ffibuilder.cdef("""
    int libusb_init(struct libusb_context** context);
    void libusb_exit(struct libusb_context* context);

    ssize_t libusb_get_device_list(
        struct libusb_context*,
        struct libusb_device***
    );

    void libusb_free_device_list(
        struct libusb_device**,
        int
    );

    void libusb_get_device_descriptor(
        struct libusb_device*,
        struct libusb_device_descriptor*
    );

    int libusb_get_port_numbers(
        struct libusb_device* dev,
        uint8_t* port_numbers,
        int port_numbers_len
    );

    struct libusb_device_descriptor {
        uint16_t idVendor;
        uint16_t idProduct;
        ...;
    };


    int libusb_open(
        struct libusb_device*,
        struct libusb_device_handle**
    );

    void libusb_close(struct libusb_device_handle*);

    int libusb_control_transfer(
        struct libusb_device_handle*,
        uint8_t,
        uint8_t,
        uint16_t,
        uint16_t,
        uint8_t*,
        uint16_t,
        unsigned int
    );

    int libusb_bulk_transfer(
        struct libusb_device_handle*,
        uint8_t,
        uint8_t*,
        int,
        int*,
        unsigned int
    );

    int libusb_interrupt_transfer(
        struct libusb_device_handle*,
        uint8_t,
        uint8_t*,
        int,
        int*,
        unsigned int
    );
""")

if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
