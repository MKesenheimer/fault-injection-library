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
from findus import PicoGlitcher, Helper
from findus.STM32Bootloader import STM32Bootloader

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

        # choose multiplexing, pulse-shaping or crowbar glitching
        if args.multiplexing:
            self.glitcher.change_config_and_reset("mux_vinit", str(args.voltage))
            self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=args.voltage)
            self.glitcher.set_multiplexing()
        elif args.pulse_shaping:
            self.glitcher.set_pulseshaping(vinit=args.voltage)

        self.bootcom = STM32Bootloader(port=self.args.target)
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

            if b'ok' in response:
                print("[+] Setting up memory read")
                response = self.bootcom.setup_memread()
                print(f"[+] Command setup_memread response: {response}")

            if b'ok' in response:
                if self.args.dump:
                    # dump memory
                    response = self.bootcom.dump_memory_to_file(self.dump_filename)
                    print(f"[+] Command dump_memory_to_file response: {response}")

                    # Dump finished
                    if response == b'success: dump finished':
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
    parser = argparse.ArgumentParser(description="Power the target via different output stages of the Pico Glitcher (VTARGET, multiplexing stage, pulse-shaping stage or external power supply) and dump the flash content of a STM32 in bootloader mode via a UART connection.")
    parser.add_argument("--target", required=True, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="")
    parser.add_argument("--dump", required=False, action='store_true')
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--multiplexing", required=False, action='store_true', help="Use the multiplexing stage to power the target (requires PicoGlitcher v2).")
    parser.add_argument("--pulse-shaping", required=False, action='store_true', help="Use the pulse-shaping stage to power the target (requires PicoGlitcher v2). Be sure to calibrate the pulse-shaping stage's voltage output.")
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