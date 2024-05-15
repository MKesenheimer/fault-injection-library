#!/usr/bin/env python3
import argparse
import re
import time
import sys
import random
import os
import logging

# import custom libraries
sys.path.insert(0, f'../FaultInjectionLib/')
from FaultInjectionLib import *

# inherit functionality and overwrite some functions
class DerivedMicroPythonScript(MicroPythonScript):
    def tick(self):
        res = self.pyb.exec(f'mp.tick()')

    def blink(self):
        res = self.pyb.exec(f'mp.blink()')

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