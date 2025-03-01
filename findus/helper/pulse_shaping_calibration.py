#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import argparse
import sys
from findus import PicoGlitcher

class Calibration():
    def __init__(self, args):
        self.args = args
        self.glitcher = PicoGlitcher()
        self.glitcher.init(port=args.rpico)
        
    def run(self):
        print("[+] Connect TRIGGER and RESET.")
        print("[+] Turn gain potentiometer of Pulse Shaping Expansion board all the way to the left (lowest gain).")
        print("[+] Connect your oscilloscope to pulse output of the Pulse Shaping Expansion board and to TRIGGER for triggering.")
        print("[+] Observe pulse.")
        print("[+] Measure maximum and minimum voltage of the generated pulse (vhigh and vlow). Take note and abort execution.")
        print("[+] Execute this script again with the found values for vhigh and vlow and check if the pulse aligns with 0V.")
        print("[+] Note that the found calibration values are stored on the Pico Glitcher persistently if this script is called with values for vlow and vhigh.")

        if self.args.vhigh != 1.0 and self.args.vlow != 0.0:
            self.glitcher.apply_calibration(self.args.vhigh, self.args.vlow, store=True)
        else:
            self.glitcher.apply_calibration(self.args.vhigh, self.args.vlow, store=False)

        while True:
            self.glitcher.do_calibration(self.args.vhigh)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=True, help="rpico port", default="/dev/ttyACM0")
    parser.add_argument("--vhigh", required=False, help="", type=float, default=1.0)
    parser.add_argument("--vlow", required=False, help="", type=float, default=0.0)
    args = parser.parse_args()

    cal = Calibration(args)

    try:
        cal.run()
    except KeyboardInterrupt:
        if args.vhigh != 1.0 and args.vlow != 0.0:
            print("[+] Calibration saved.")
        print("\nExitting...")
        sys.exit(1)

if __name__ == "__main__":
    main()
