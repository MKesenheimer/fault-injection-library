#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import argparse
import sys
import time

# import custom libraries
from findus import MicroPythonScript

# inherit functionality and overwrite some functions
class DerivedMicroPythonScript(MicroPythonScript):
    def tick(self):
        self.pyb.exec('mp.tick()')

    def enable_vtarget(self):
        self.pyb.exec('mp.enable_vtarget()')

    def disable_vtarget(self):
        self.pyb.exec('mp.disable_vtarget()')

    def enable_glitch(self):
        self.pyb.exec('mp.enable_glitch()')

    def disable_glitch(self):
        self.pyb.exec('mp.disable_glitch()')

    def enable_hpglitch(self):
        self.pyb.exec('mp.enable_hpglitch()')

    def disable_hpglitch(self):
        self.pyb.exec('mp.disable_hpglitch()')

    def enable_lpglitch(self):
        self.pyb.exec('mp.enable_lpglitch()')

    def disable_lpglitch(self):
        self.pyb.exec('mp.disable_lpglitch()')

    def reset_target(self):
        self.pyb.exec('mp.reset_target()')

    def release_reset(self):
        self.pyb.exec('mp.release_reset()')

class Main():
    def __init__(self, args):
        self.args = args
        self.micropython = DerivedMicroPythonScript()
        self.micropython.init(self.args.rpico, 'mpBlink')

    def run(self):
        while True:
            self.micropython.tick()
            self.micropython.disable_vtarget()
            self.micropython.disable_glitch()
            self.micropython.disable_hpglitch()
            self.micropython.disable_lpglitch()
            self.micropython.reset_target()
            time.sleep(0.5)
            self.micropython.enable_vtarget()
            self.micropython.enable_glitch()
            self.micropython.enable_hpglitch()
            self.micropython.enable_lpglitch()
            self.micropython.release_reset()
            time.sleep(0.5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico",  required=False, help="rpico port", default="/dev/ttyACM1")
    args = parser.parse_args()

    test = Main(args)

    try:
        test.run()
    except KeyboardInterrupt:
        print('\nExitting...')
        sys.exit(1)