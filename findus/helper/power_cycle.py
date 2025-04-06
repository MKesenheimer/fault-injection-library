#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import argparse
import sys
import time
from findus import PicoGlitcher

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
            self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=args.voltage)

        # choose multiplexing, pulse-shaping or crowbar glitching
        if args.multiplexing:
            self.glitcher.change_config_and_reset("mux_vinit", str(args.voltage))
            self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=args.voltage)
            self.glitcher.set_multiplexing()
        elif args.pulse_shaping:
            self.glitcher.set_pulseshaping(vinit=args.voltage)

    def run(self):
        print("[+] Power cycling target")
        # power cycle target
        self.glitcher.power_cycle_target(1)
        self.glitcher.reset(0.01)
        time.sleep(0.2)

def main(argv=sys.argv):
    parser = argparse.ArgumentParser(description="Power-cycle the target via different output stages of the Pico Glitcher (VTARGET, multiplexing stage, pulse-shaping stage or external power supply).")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyACM0")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--multiplexing", required=False, action='store_true', help="Use the multiplexing stage to power-cycle the target (requires PicoGlitcher v2).")
    parser.add_argument("--pulse-shaping", required=False, action='store_true', help="Use the pulse-shaping stage to power-cycle the target (requires PicoGlitcher v2). Be sure to calibrate the pulse-shaping stage's voltage output.")
    parser.add_argument("--voltage", required=False, help="The voltage to set. Note that the voltage output of the pulse-shaping stage can not be controlled with this parameter. The voltage output of the pulse-shaping stage must be set manually with the potentiometer.", type=float, default=3.3)
    args = parser.parse_args()

    pc = PowerCycler(args)

    try:
        pc.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)

if __name__ == "__main__":
    main()