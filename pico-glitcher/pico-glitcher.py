# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

#!/usr/bin/env python3
import argparse
import time
import sys
import random
import logging

# import custom libraries
sys.path.insert(0, '../lib/')
from FaultInjectionLib import PicoGlitcher, Database, Serial

# inherit functionality and overwrite some functions
class DerivedGlitcher(PicoGlitcher):
    def classify(self, expected, response):
        if response == expected:
            color = 'G'
        elif b'Falling' in response:
            color = 'R'
        elif b'Fatal exception' in response:
            color = 'M'
        else:
            color = 'Y'
        return color

class Main():
    def __init__(self, args):
        self.args = args

        logging.basicConfig(filename='execution.log', filemode='a', format='%(asctime)s %(message)s', level=logging.INFO, force=True)

        self.glitcher = DerivedGlitcher()
        self.glitcher.init(port=args.rpico)

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume)

        self.target = Serial(port=self.args.target, timeout=0.1)
        self.target.init()

        self.start_time = int(time.time())

    def __del__(self):
        try:
            self.target.close()
        except:
            pass

    def run(self):
        # log execution
        logging.info(' '.join(sys.argv))

        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay  = self.args.delay[0]
        e_delay  = self.args.delay[1]

        expected = b'ets Jun  8 2016 00:22:57\r\n\r\nrst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)\r\nconfigsip: 0, SPIWP:0xee\r\nclk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00\r\nmode:DOUT, clock div:2\r\nload:0x40080400,len:16384\r\ncsum err:0xef!=0xff\r\nets_main.c 371 \r\n'

        experiment_id = 0
        while True:
            # empty rx buffer
            self.target.empty_read_buffer()

            # set up glitch parameters (in nano seconds) and arm glitcher
            length = random.randint(s_length, e_length)
            delay = random.randint(s_delay, e_delay)
            self.glitcher.arm(delay, length)

            # power cycle
            #self.glitcher.power_cycle_target(0.5)
            #time.sleep(0.05)

            # reset target
            self.glitcher.reset(0.01)
            time.sleep(0.01)

            # send command and read response
            response = self.target.read(len(expected))

            # block execution until glitch was sent
            self.glitcher.block()

            # classify response
            color = self.glitcher.classify(expected, response)

            # add to database
            self.database.insert(experiment_id, delay, length, color, response)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{length}\t{delay}\t{color}\t{response}", color))

            # increase experiment id
            experiment_id += 1
            
        self.target.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico",  required=False, help="rpico port", default="/dev/ttyACM1")
    parser.add_argument("--delay",  required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length",  required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    args = parser.parse_args()

    pico_glitcher = Main(args)

    try:
        pico_glitcher.run()
    except KeyboardInterrupt:
        print('\nExitting...')
        sys.exit(1)