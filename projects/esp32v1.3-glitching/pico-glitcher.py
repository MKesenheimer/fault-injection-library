#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# This script can be used to test the pico-glitcher.
# -> Connect Trigger input with Reset.
# -> Between Glitch and VTarget, connect a 10 Ohm resistor (this is the test target).
# -> Run the script:
# python pico-glitcher.py --rpico /dev/tty.usbmodem1101 --delay 100 100 --length 100 100
# -> You should now be able to observe the glitches with a oscilloscope on the 10 Ohm resistor.
# -> measure the expected delay and glitch length.

import argparse
import logging
import random
import sys
import time

# import custom libraries
from findus import Database, PicoGlitcher, Serial
from findus import OptimizationController

# inherit functionality and overwrite some functions
class DerivedGlitcher(PicoGlitcher):
    def classify(self, response):
        if b'XXXX00000400YYYY00000400ZZZZ\r\n' in response:
            color, weight = 'G', 0
        elif b'' == response:
            color, weight = 'M', 0
        elif b'Error' in response:
            color, weight = 'M', 0
        elif b'Fatal exception' in response:
            color, weight = 'M', 1
        elif b'Timeout' in response:
            color, weight = 'Y', -5
        else:
            color, weight = 'R', 10
        return color, weight

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
        # choose rising edge trigger with dead time of 0 seconds after power down
        # note that you still have to physically connect the trigger input with vtarget
        self.glitcher.rising_edge_trigger(pin_trigger=args.trigger_input)

        # choose pulse shaping or crowbar glitching
        if args.pulse_shaping:
            self.glitcher.set_pulse_shaping()
        else:
            self.glitcher.set_lpglitch()

        # target communication
        self.target = Serial(port=args.target, baudrate=115200)
        time.sleep(0.01)
        self.glitcher.reset(0.01)
        print(self.target.read(1024))

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)
        self.start_time = int(time.time())

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_t1 = 0
        e_t1 = 2000
        s_t3 = 0
        e_t3 = 2000

         # Genetic Algorithm to search for the best performing bin
        boundaries = [(s_delay, e_delay), (s_t1, e_t1), (s_length, e_length), (s_t3, e_t3)]
        divisions = [10, 10, 5, 10]
        opt = OptimizationController(parameter_boundaries=boundaries, parameter_divisions=divisions, number_of_individuals=10, length_of_genom=20)

        experiment_id = 0
        while True:
            # get the next parameter set
            delay, t1, length, t3 = opt.step()
            if experiment_id % 100 == 0:
                boundaries = opt.get_best_performing_bins()
                print("[+] Best performing bin:")
                for b in boundaries:
                    print(b)

            # arm
            if args.pulse_shaping:
                pulse_config = {"t1": t1, "v1": "1.8", "t2": length, "v2": "GND", "t3": t3, "v3": "1.8"}
                self.glitcher.arm_pulse_shaping(delay, pulse_config)
            else:
                self.glitcher.arm(delay, length)

            # initialize the loop on the ESP32
            self.target.write(b'A')

            # block until glitch and read response
            try:
                self.glitcher.block(timeout=0.5)
                response = self.target.read(30)
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.reset(0.01)
                #time.sleep(0.01)
                #self.target.flush_v2()
                self.target.read(1024)
                response = b'Timeout'

            # classify response
            color, weight = self.glitcher.classify(response)

            # add to database
            self.database.insert(experiment_id, delay, length, color, response)

            # add experiment to parameterspace of genetic algorithm
            opt.add_experiment(weight, delay, t1, length, t3)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{length}\t{delay}\t{color}\t{response}", color))

            # increase experiment id
            experiment_id += 1

            # stop after enough data captured
            #if experiment_id >= 5000:
            #    break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyACM0")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--pulse-shaping", required=False, action='store_true', help="Instead of crowbar glitching, perform a fault injection with pulse shaping (requires PicoGlitcher v2).")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)
