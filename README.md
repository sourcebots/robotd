robot control daemon
====================

Runs a master process which monitors for Robot peripherals. For each one it
finds, it opens a UNIX seqpacket socket in /var/robotd/<type>/<id> and runs
a controller process to actually communicate with the board.

Currently just handles the motor board.

Tour of the source
------------------

* `robotd/master.py` contains the main entry point, the UNIX socket listening
  code, and the bits to launch controller subprocesses.
* `robotd/devices.py` contains the actual classes which implement particular
  devices.
* `robotd/devices_base.py` contains some common code for `devices.py`.
* `robotd.service` is the systemd service which runs the thing in production.

Building the Debian package
---------------------------

Install through apt:

* `build-essential`
* `devscripts`
* `debhelper`
* `dh-systemd`

And then run, from the root of the project:

* `debuild -uc -us`
