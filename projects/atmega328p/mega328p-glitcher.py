#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# This script can be used to test the pico-glitcher.
# -> Connect Trigger input with Reset.
# -> Between Glitch and VTarget, connect a 10 Ohm resistor (this is the "device under test").
# -> Run the script:
# python pico-glitcher.py --rpico /dev/tty.usbmodem1101 --delay 100 100 --length 100 100
# -> You should now be able to observe the glitches with a oscilloscope on the 10 Ohm resistor.
# -> measure the expected delay and glitch length.

import argparse
import logging
import random
import sys
import time
import subprocess

# import custom libraries
from findus import Database, PicoGlitcher

# inherit functionality and overwrite some functions
class DerivedGlitcher(PicoGlitcher):
    def classify(self, response):
        if b'Error' in response:
            color = 'M'
        elif b'0xff' in response:
            color = 'G'
        elif b'Fatal exception' in response:
            color = 'M'
        elif b'Timeout' in response:
            color = 'Y'
        else:
            color = 'R'
        return color

# read lock bits with avrdude
# > avrdude -F -c jtag3isp -p m328p -U lock:r:-:h
def read_lock_bits():
    subout = subprocess.run(['avrdude',
                          '-F',
                          '-c', 'jtag3isp',
                          '-p', 'm328p',
                          '-U', 'lock:r:-:h',
                          '-B', '125000'],
                          check=False, capture_output=True)
    response = subout.stdout + subout.stderr
    return response

class Main():
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = DerivedGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # the initial voltage for multiplexing must be hard-coded and can only be applied
        # if the raspberry pi pico is reset and re-initialized.
        if args.multiplexing:
            self.glitcher.change_config_and_reset("mux_vinit", "VI2")
            self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # choose rising edge trigger
        #self.glitcher.rising_edge_trigger(pin_trigger=args.trigger_input)
        #self.glitcher.edge_count_trigger(pin_trigger=args.trigger_input, number_of_edges=2, edge_type="rising")
        #self.glitcher.falling_edge_trigger(pin_trigger=args.trigger_input)
        self.glitcher.edge_count_trigger(pin_trigger=args.trigger_input, number_of_edges=2, edge_type="falling")

        # choose multiplexing, pulse-shaping or crowbar glitching
        if args.multiplexing:
            self.glitcher.set_multiplexing()
        elif args.pulse_shaping:
            self.glitcher.set_pulseshaping(vinit=3.3)
        else:
            self.glitcher.set_lpglitch()

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

        # release reset (not relevant here, since reset is triggered by avrdude)
        self.glitcher.release_reset()

        experiment_id = 0
        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            # trunk-ignore(bandit/B311)
            delay = random.randint(s_delay, e_delay)
            # trunk-ignore(bandit/B311)
            length = random.randint(s_length, e_length)

            # arm
            if args.multiplexing:
                mul_config = {"t1": length, "v1": "1.8", "t2": length, "v2": "VI1", "t3": length, "v3": "VI2",  "t4": length, "v4": "GND"}
                self.glitcher.arm_multiplexing(delay, mul_config)
            elif args.pulse_shaping:
                # pulse from lambda; ramp down to 1.8V than GND glitch
                ps_lambda = f"lambda t:-1.5/({2*length})*t+3.3 if t<{2*length} else 1.8 if t<{4*length} else 0.0 if t<{5*length} else 3.3"
                self.glitcher.arm_pulseshaping_from_lambda(delay, ps_lambda, 6*length)
            else:
                # burst
                #self.glitcher.arm(delay, length, 10, 1000)
                # one shot
                self.glitcher.arm(delay, length)

            # read lock bits (this triggers the glitch)
            response = read_lock_bits()
            
            # block until glitch
            try:
                self.glitcher.block(timeout=1)
            except Exception as e:
                print(e)
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_target(power_cycle_time=1)
                time.sleep(0.2)
                response = b'Timeout: Trigger not observed.'

            # classify response
            color = self.glitcher.classify(response)

            # add to database
            self.database.insert(experiment_id, delay, length, color, response)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{length}\t{delay}\t{color}\t{response}", color))

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
    parser.add_argument("--multiplexing", required=False, action='store_true', help="Instead of crowbar glitching, perform a fault injection with multiplexing between different voltages (requires PicoGlitcher v2).")
    parser.add_argument("--pulse-shaping", required=False, action='store_true', help="Instead of crowbar glitching, perform a fault injection with a predefined voltage profile (requires PicoGlitcher v2).")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")

    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)
