#!/usr/bin/env python3
import argparse
import logging
import random
import sys
import time
import serial

# import custom libraries
sys.path.insert(0, "../lib/")
import bootloader_com
from FaultInjectionLib import Database, ProGlitcher

glitcher = ProGlitcher()
ser = serial.Serial(port="/dev/ttyUSB0", baudrate=115200, timeout=0.25, bytesize=8, parity='E', stopbits=1)
glitcher.init()

while True:
    # reset target
    #glitcher.reset(0.01)
    glitcher.power_cycle_target()
    time.sleep(0.5)

    # setup bootloader communication
    response = bootloader_com.bootloader_setup_memread(ser)
    print(response)
    
    # power cycle if unavailable
    #if response == -1:
    #    glitcher.power_cycle_target()