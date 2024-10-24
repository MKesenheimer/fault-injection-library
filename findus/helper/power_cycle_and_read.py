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
from findus import ProGlitcher, PicoGlitcher, Helper
from findus.BootloaderCom import BootloaderCom, GlitchState
from findus.GlitchState import OKType

class PowerCycler:
    def __init__(self, args):
        self.args = args

        if self.args.rpico == "":
            print("[+] Initializing ProGlitcher")
            self.glitcher = ProGlitcher()
            self.glitcher.init()
        else:
            print("[+] Initializing PicoGlitcher")
            self.glitcher = PicoGlitcher()
            self.glitcher.init(port=args.rpico)

        self.bootcom = BootloaderCom(port=self.args.target)
        self.dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

    def run(self):
        while True:
            print("[+] Power cycling target")
            # reset target
            self.glitcher.power_cycle_target()
            self.glitcher.reset(0.01)
            time.sleep(0.2)

            # setup bootloader communication
            print("[+] Initializing bootloader")
            response = self.bootcom.init_bootloader()
            print(f"[+] Command init_bootloader response: {response}")

            if issubclass(type(response), OKType):
                print("[+] Setting up memory read")
                response = self.bootcom.setup_memread()
                print(f"[+] Command setup_memread response: {response}")

            if issubclass(type(response), OKType):
                if self.args.dump:
                    # dump memory
                    response = self.bootcom.dump_memory_to_file(self.dump_filename)
                    print(f"[+] Command dump_memory_to_file response: {response}")

                    # Dump finished
                    if response == GlitchState.Success.dump_finished:
                        break
                else:
                    start = 0x08000000
                    size  = 0xff
                    print("[+] Reading memory")
                    response, mem = self.bootcom.read_memory(start, size)
                    print(f"[+] Command read_memory response: {response}")
                    print(mem)
                    #break

def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="")
    parser.add_argument("--dump", required=False, action='store_true')
    args = parser.parse_args()

    pc = PowerCycler(args)

    try:
        pc.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)

if __name__ == "__main__":
    main()