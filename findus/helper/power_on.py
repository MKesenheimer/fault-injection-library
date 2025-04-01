#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import argparse
import sys
import time
from findus import PicoGlitcher, Helper

class PowerCycler:
    def __init__(self, args):
        self.args = args

        if self.args.rpico == "":
            print("[+] Initializing ProGlitcher")
            from findus.ProGlitcher import ProGlitcher
            self.glitcher = ProGlitcher()
            self.glitcher.init()
        else:
            print("[+] Initializing PicoGlitcher")
            self.glitcher = PicoGlitcher()
            self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

    def run(self):
        print("[+] Enabling VTARGET. Press Ctrl-C to disable.")
        # power cycle target
        self.glitcher.power_cycle_target(1)
        self.glitcher.reset(0.01)
        while True:
            time.sleep(0.2)

def main(argv=sys.argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=False, help="rpico port", default="")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    args = parser.parse_args()

    pc = PowerCycler(args)

    try:
        pc.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)

if __name__ == "__main__":
    main()