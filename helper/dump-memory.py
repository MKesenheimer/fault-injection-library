# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

#!/usr/bin/env python3
import argparse
import sys
import time

# import custom libraries
sys.path.insert(0, "../lib/")
from BootloaderCom import BootloaderCom
from FaultInjectionLib import PicoGlitcher, Helper

class Main:
    def __init__(self, args):
        self.args = args

        self.glitcher = PicoGlitcher()
        self.glitcher.init(port=args.rpico)

        self.bootcom = BootloaderCom(port=self.args.target, dump_address=0x08000000, dump_len=0x400)
        self.dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

    def run(self):
        while True:
            # reset target
            self.glitcher.reset(0.01)
            #self.glitcher.power_cycle_target()
            time.sleep(0.01)

            # setup bootloader communication
            response = self.bootcom.init_get_id()

            if response == 0:
                # dump memory, this function triggers the glitch
                response = self.bootcom.dump_memory_to_file(self.dump_filename)

            if response == 1:
                # Dump finished
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyACM1")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)