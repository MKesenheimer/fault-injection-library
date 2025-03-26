#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# SQL Queries:
# Show only successes and flash-resets:
# color = 'R' or response LIKE '_Warning.flash_reset'

import argparse
import logging
import random
import sys
import time
import re

# import custom libraries
from findus import DebugInterface, Database, PicoGlitcher, Helper

def extract(response, register):
    match = re.search(rf"{register}.*?(0x[0-9a-fA-F]+)", response)
    if match:
        return match.group(1)
    return None

class Main:
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = PicoGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # STLink Debugger
        #self.debugger = DebugInterface(tool="stlink", processor="stm32l0", transport="hla_swd", gdb_exec="gdb-multiarch")
        self.debugger = DebugInterface(tool="stlink", processor="stm32l0", transport="hla_swd")

        # programming the target
        if args.program_target != None:
            print("[+] Programming target.")
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-STM32L0.elf", rdp_level=args.program_target, verbose=True)

    def cleanup(self):
        self.debugger.detach()

    def run(self):
        # bring the target to a known state
        self.glitcher.power_cycle_reset()
        time.sleep(0.1)

        # attach debugger
        self.debugger.attach()
        time.sleep(0.1)
        self.debugger.telnet_init()

        # send commands and observe response
        # 0x8000118: main()
        # 0x8000122: SystemInit()
        # 0x80003d8: Reset_Handler()
        address = 0x00
        for delta in range(0, 0x400, 4):
            print(f"[+] Checking address {hex(address + delta)}")
            self.debugger.telnet_interact("reset halt", verbose=False)
            for i in range(0, 13):
                self.debugger.telnet_interact(f"reg r{i} {hex(address + delta)}", verbose=False)
            self.debugger.telnet_interact(f"reg pc {hex(address + delta)}", verbose=False)
            self.debugger.telnet_interact(f"step", verbose=False)
            response = self.debugger.telnet_interact(f"reg", wait_time=0.1, verbose=True)

            # check for differences
            for i in range(0, 13):
                mem = extract(response, f"r{i}")
                if mem is not None:
                    value = int(mem, 16)
                    if value != address + delta:
                        print(f"r{i} = {hex(value)}\n")
        
        self.debugger.detach()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--program-target", required=False, metavar="RDP_LEVEL", type=int, default=None, help="Reprogram the target before glitching and set the RDP level.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        main.cleanup()
        sys.exit(1)