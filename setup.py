#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name='robotd',
    version='1.0',
    description="Daemon for vision code for Source Bots",
    author="SourceBots",
    author_email='',
    packages=find_packages(),
    setup_requires=[
        'cffi>=1.4.0',
    ],
    cffi_modules=[
        'robotd/native/apriltag/apriltag_build.py:ffi',
        'robotd/native/libusb_build.py:ffibuilder',
    ],
    install_requires=[
        'pyudev',
        'pyserial',
        'pygame',
        'Pillow',
        "cffi>=1.4.0",
        'numpy',
        'setproctitle',
    ],
    zip_safe=False,
)
