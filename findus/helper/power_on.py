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
            if args.power is not None:
                self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=float(args.voltage), enable_vtarget=False)
            else:
                self.glitcher.init(port=args.rpico, enable_vtarget=False)

        # choose multiplexing, pulse-shaping or crowbar glitching
        if args.multiplexing:
            self.glitcher.change_config_and_reset("mux_vinit", args.voltage)
            self.glitcher.init(port=args.rpico, enable_vtarget=False)
            self.glitcher.set_multiplexing()
        elif args.pulse_shaping:
            self.glitcher.set_pulseshaping(vinit=float(args.voltage))

        if args.enable_bootloader:
            self.glitcher.set_gpio(pin_number=4, value=1) # BOOT0
            self.glitcher.set_gpio(pin_number=5, value=0) # BOOT1

    def run(self):
        print("[+] Enabling VTARGET. Press Ctrl-C to disable.")
        # power cycle target
        self.glitcher.power_cycle_reset(1)
        #self.glitcher.reset(0.01)
        while True:
            time.sleep(0.2)

def main(argv=sys.argv):
    parser = argparse.ArgumentParser(description="Power the target via different output stages of the Pico Glitcher (VTARGET, multiplexing stage, pulse-shaping stage or external power supply).")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyACM0")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--multiplexing", required=False, action='store_true', help="Use the multiplexing stage to power the target (requires PicoGlitcher v2).")
    parser.add_argument("--pulse-shaping", required=False, action='store_true', help="Use the pulse-shaping stage to power the target (requires PicoGlitcher v2). Be sure to calibrate the pulse-shaping stage's voltage output.")
    parser.add_argument("--voltage", required=False, help="The voltage to set for the external power supply or the multiplexer stage. Can either be a float value when using the external power supply, or one of [\"GND\", \"VI1\", \"VI2\", \"3.3\", \"1.8\"] when using the multiplexer stage. Note that the voltage output of the pulse-shaping stage can not be controlled with this parameter. The voltage output of the pulse-shaping stage must be set manually with the potentiometer.", type=str, default="3.3")
    parser.add_argument("--enable-bootloader", required=False, action='store_true', help="")
    args = parser.parse_args()

    pc = PowerCycler(args)

    try:
        pc.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)

if __name__ == "__main__":
    main()