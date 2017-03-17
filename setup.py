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
        'cffi>=0.8.6',
    ],
    ffi_modules=[
        'robotd/vision/apriltag/apriltag_build.py:ffibuilder',
    ],
    install_requires=[
        'pyudev',
        'pyserial',
        'pygame',
        'Pillow',
        "cffi>=0.8.6",
        'numpy',
        'setproctitle',
    ],
)
