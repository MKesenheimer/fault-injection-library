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
from findus import Database, PicoGlitcher
from findus import OptimizationController

# inherit functionality and overwrite some functions
class DerivedGlitcher(PicoGlitcher):
    def classify(self, response):
        if b'Trigger ok' in response:
            color, weight = 'G', 0
        elif b'Error' in response:
            color, weight = 'M', 0
        elif b'Fatal exception' in response:
            color, weight = 'M', 0
        elif b'Timeout' in response:
            color, weight = 'Y', -1
        else:
            color, weight = 'R', 2
        return color, weight

class Main():
    def __init__(self, args):
        self.args = args
        self.vinit = 2.1

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = DerivedGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # choose rising edge trigger with dead time of 0 seconds after power down
        # note that you still have to physically connect the trigger input with vtarget
        self.glitcher.rising_edge_trigger(pin_trigger=args.trigger_input)

        # pulse-shape glitching
        self.glitcher.set_pulseshaping(vinit=self.vinit)

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "t1", "v1", "t2", "v2", "t3", "v3", "t4"])
        self.start_time = int(time.time())

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        vmin = 0.0 # this voltage is capped at that what the DAC can provide.
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_t1 = 10
        e_t1 = 70
        s_v1 = vmin
        e_v1 = self.vinit
        s_t2 = 10
        e_t2 = 70
        s_v2 = vmin
        e_v2 = self.vinit
        s_t3 = 10
        e_t3 = 70
        s_v3 = vmin
        e_v3 = self.vinit
        s_t4 = 10
        e_t4 = 70

        # Genetic Algorithm to search for the best performing bin
        boundaries = [(s_delay, e_delay), (s_t1, e_t1), (s_v1, e_v1), (s_t2, e_t2), (s_v2, e_v2), (s_t3, e_t3), (s_v3, e_v3), (s_t4, e_t4)]
        divisions = [10, 5, 5, 5, 5, 5, 5, 5]
        opt = OptimizationController(parameter_boundaries=boundaries, parameter_divisions=divisions, number_of_individuals=10, length_of_genom=20, malus_factor_for_equal_bins
        =1)

        experiment_id = 0
        while True:
            # get the next parameter set
            delay, t1, v1, t2, v2, t3, v3, t4 = opt.step()
            if experiment_id % 100 == 0:
                opt.print_best_performing_bins()

            # arm
            tpoints = [         0, t1, t1, t1 + t2, t1 + t2 + t3, t1 + t2 + t3 + t4]
            vpoints = [self.vinit, v1, v1,      v2,           v3,        self.vinit]
            self.glitcher.arm_pulseshaping_from_spline(delay, tpoints, vpoints)

            # reset target
            time.sleep(0.01)
            self.glitcher.reset(0.01)

            # block until glitch
            try:
                self.glitcher.block(timeout=2)
                # Manually set the response to a reasonable value.
                # In a real scenario, this would be filled by the response of the microcontroller (UART, SWD, etc.)
                response = b'Trigger ok'
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_target(power_cycle_time=1)
                time.sleep(0.2)
                response = b'Timeout'

            # classify response
            color, weight = self.glitcher.classify(response)

            # add to database
            self.database.insert(experiment_id, delay, t1, v1, t2, v2, t3, v3, t4, color, response)

            # add experiment to parameterspace of genetic algorithm
            opt.add_experiment(weight, delay, t1, v1, t2, v2, t3, v3, t4)
            #opt.add_experiment(weight, delay, length)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{int(delay)}\t{int(t1)}\t{int(v1)}\t{int(t2)}\t{int(v2)}\t{int(t3)}\t{int(v3)}\t{int(t4)}\t{color}\t{response}", color))

            # increase experiment id
            experiment_id += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyACM0")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)
