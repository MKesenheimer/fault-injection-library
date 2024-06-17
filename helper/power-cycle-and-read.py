#!/usr/bin/env python3
import sys
import time

# import custom libraries
sys.path.insert(0, "../lib/")
from BootloaderCom import BootloaderCom
from FaultInjectionLib import ProGlitcher

def init(port="/dev/ttyUSB0"):
    print("[+] Initializing ProGlitcher")
    global glitcher
    glitcher = ProGlitcher()
    glitcher.init()
    global bootcom
    bootcom = BootloaderCom(port=port)

def power_cycle_read():
    print("[+] Power cycling target")
    global glitcher
    global bootcom

    # reset target
    #glitcher.reset(0.01)
    glitcher.power_cycle_target()
    time.sleep(0.2)

    # setup bootloader communication
    print("[+] Reading chip ID")
    response = bootcom.init_get_id()
    print(response)

    if response == 0:
        print("[+] Setting up memory read")
        response = bootcom.setup_memread()
        print(response)

    if response == 0:
        start = 0x08000000
        size  = 0xff
        print("[+] Reading memory")
        response, mem = bootcom.read_memory(start, size)
        print(response)

    if response == 0:
        print(mem)

if __name__ == "__main__":
    try:
        init(port=sys.argv[1])
        while True:
            power_cycle_read()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)