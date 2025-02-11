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
from findus.InteractivePchipEditor import InteractivePchipEditor
from findus.firmware.Spline import Spline

# inherit functionality and overwrite some functions
class DerivedGlitcher(PicoGlitcher):
    def classify(self, response):
        if b'Trigger ok' in response:
            color = 'G'
        elif b'Error' in response:
            color = 'M'
        elif b'Fatal exception' in response:
            color = 'M'
        elif b'Timeout' in response:
            color = 'Y'
        else:
            color = 'R'
        return color

def pulse_from_lambda(ps_lambda) -> list[int]:
        pulse = [0] * 512
        t = 0
        dt = 10
        for i in range(512):
            pulse[i] = int(ps_lambda(t) * 816)
            t += dt
        return pulse

class Main():
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = DerivedGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)
        # choose rising edge trigger with dead time of 0 seconds after power down
        # note that you still have to physically connect the trigger input with vtarget

        #self.glitcher.waveform_generator(frequency=100_000, gain=1, waveid=0)
        #sys.exit(0)

        self.glitcher.rising_edge_trigger(pin_trigger=args.trigger_input)

        # pulse-shape glitching
        self.glitcher.set_pulseshaping(vinit=3.3)

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)
        self.start_time = int(time.time())

        # load the interactive piecewise cubic hermite interpolating polynomial editor
        if args.pulse_type == 6:
            self.editor = InteractivePchipEditor()

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
            # trunk-ignore(bandit/B311)
            delay = random.randint(s_delay, e_delay)
            # trunk-ignore(bandit/B311)
            length = random.randint(s_length, e_length)

            # arm
            # pulse shaping with config (without interpolation, like multiplexing)
            if args.pulse_type == 0:
                ps_config = [[length, 2.0], [length, 1.0], [length, 0.0], [length, 3.0]]
                self.glitcher.arm_pulseshaping_from_config(delay, ps_config)

            # pulse from lambda
            elif args.pulse_type == 1:
                ps_lambda = f"lambda t:2.0 if t<{length} else 1.0 if t<{2*length} else 0.0 if t<{3*length} else 3.0"
                self.glitcher.arm_pulseshaping_from_lambda(delay, ps_lambda, 10*length)

            # pulse from raw list
            elif args.pulse_type == 2:
                pulse = [-0x1fff] * 50 + [-0x0fff] * 50 + [-0x07ff] * 50 + [0x0000] * 50
                self.glitcher.arm_pulseshaping_from_list(delay, pulse)

            # pulse from lambda; ramp down to 1.8V than GND glitch
            elif args.pulse_type == 3:
                    ps_lambda = f"lambda t:-1.0/({2*length})*t+3.0 if t<{2*length} else 2.0 if t<{4*length} else 0.0 if t<{5*length} else 3.0"
                    self.glitcher.arm_pulseshaping_from_lambda(delay, ps_lambda, 6*length)

            # pulse from points -> interpolation is used
            elif args.pulse_type == 5:
                    xpoints = [0,   100, 200, 300, 400, 500, 515, 520]
                    ypoints = [3.3, 2.1, 2.0, 2.0, 1.7, 0.0, 2.0, 3.3]
                    self.glitcher.arm_pulseshaping_from_spline(delay, xpoints, ypoints)
                    Spline.interpolate_and_plot(xpoints, ypoints)

            # pulse defined from interactive editor
            elif args.pulse_type == 6:
                self.editor.show(block=False)
                xpoints, ypoints = self.editor.get_points()
                self.glitcher.arm_pulseshaping_from_spline(delay, xpoints, ypoints)

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
            color = self.glitcher.classify(response)

            # add to database
            self.database.insert(experiment_id, delay, length, color, response)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{response}", color))

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
    parser.add_argument("--pulse-type", required=True, help="Choose with which method the pulse is generated. Choose one of [0, 1, 2, 3, 4].", type=int)
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)
