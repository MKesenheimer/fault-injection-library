#!/usr/bin/env python3
import sys
import time


# import custom libraries
sys.path.insert(0, "../lib/")
from BootloaderCom import BootloaderCom
from FaultInjectionLib import ProGlitcher

def main():
    print("[+] Initializing ProGlitcher")
    glitcher = ProGlitcher()
    glitcher.init()
    bootcom = BootloaderCom(port="/dev/ttyUSB0")
    mem = b""
    while True:
        # reset target
        #glitcher.reset(0.01)
        glitcher.power_cycle_target()
        time.sleep(0.2)

        # setup bootloader communication
        response = bootcom.init_get_id()
        print(response)

        if response == 0:
            response = bootcom.setup_memread()
            print(response)

        if response == 0:
            start = 0x08000000
            size  = 0xff
            response, mem = bootcom.read_memory(start, size)
            print(response)

        if response == 0:
            print(mem)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)