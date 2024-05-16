# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

#!/usr/bin/env python3
import argparse
import sys

# import custom libraries
sys.path.insert(0, '../lib/')
from FaultInjectionLib import MicroPythonScript

# inherit functionality and overwrite some functions
class DerivedMicroPythonScript(MicroPythonScript):
    def tick(self):
        self.pyb.exec('mp.tick()')

    def blink(self):
        self.pyb.exec('mp.blink()')

class Main():
    def __init__(self, args):
        self.args = args
        self.micropython = DerivedMicroPythonScript()
        self.micropython.init(self.args.rpico, 'mp_blink')

    def run(self):
        # call micropython function
        self.micropython.tick()
        #self.micropython.blink()

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