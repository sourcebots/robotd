robot control daemon
====================

Runs a master process which monitors for Robot peripherals. For each one it
finds, it opens a UNIX seqpacket socket in `/var/robotd/<type>/<id>` and runs
a controller process to actually communicate with the board.

Currently just handles the motor board and cameras

Tour of the source
------------------

* `robotd/master.py` contains the main entry point, the UNIX socket listening
  code, and the bits to launch controller subprocesses.
* `robotd/devices.py` contains the actual classes which implement particular
  devices.
* `robotd/devices_base.py` contains some common code for `devices.py`.
* `robotd.service` is the systemd service which runs the thing in production.

Getting started
---------------

Since `robotd` vendors in April Tags for its vision support, which depends on
`libusb`, you'll need to install the development package for `libusb` in order
to build the python package:

``` bash
sudo apt install libusb-1.0-0-dev
```

Without this you'll likely see errors building the apriltags source. However,
once done you can `pip install -e .` as usual.

Building the debian package
---------------------------

Ensure

```
# Install build tools:
sudo apt install build-essential devscripts debhelper dh-systemd

# Install dependencies
sudo apt install libusb-1.0-0-dev python3-cffi

# cd to the root of this project
cd path/to/robotd

# Build the package:
debuild -uc -us
```
