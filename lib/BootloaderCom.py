# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import serial
import time
from functools import reduce
import sys
import random

class BootloaderCom:
    NACK = b'\x1f'
    ACK  = b'\x79'
    verbose = False

    def __init__(self, port, dump_address=0x08000000, dump_len=0x400):
        print(f"[+] Opening serial port {port}.")
        self.ser = serial.Serial(port=port, baudrate=115200, timeout=0.25, bytesize=8, parity="E", stopbits=1)
        # memory read settings
        self.current_dump_addr = dump_address
        self.current_dump_len = dump_len

    def check_ack(self):
        s = self.ser.read(1)
        if s != self.ACK:
            #print(s)
            return 0
        return 1

    def flush(self):
        # read garbage and discard
        self.ser.read(1024)

    def init_get_id(self):
        # init bootloader
        self.ser.write(b'\x7f')
        if self.check_ack() == 0:
            return -1

        # get chip id command (x02: chip id, xfd: crc)
        self.ser.write(b'\x02\xfd')
        if self.check_ack() == 0:
            return -2
        
        # read chip id
        s = self.ser.read(3)
        id = s[1:3]

        if self.verbose:
            print(f"Chip ID: {id}")

        if self.check_ack() == 0:
            return -3
        return 0

    def setup_memread(self, set_trigger_out=None):
        # read memory (x11: read memory, xee: crc)
        if set_trigger_out is not None:
            set_trigger_out(True)
        self.ser.write(b'\x11\xee')
        if set_trigger_out is not None:
            set_trigger_out(False)

        # if rdp is activated, a nack is returned (x1f)
        if self.check_ack() == 0:
            if self.verbose:
                print("RDP is active. Can not read memory.")
            return -4
        else:
            if self.verbose:
                print("RDP is not active. Memory read command available.")
        return 0

    def read_memory(self, start, size):
        # write memory address
        startb = start.to_bytes(4, 'big')
        crc = reduce(lambda x, y: x ^ y, startb, 0).to_bytes(1, 'big')
        self.ser.write(startb)
        self.ser.write(crc)
        if self.check_ack() == 0:
            return -5, b''

        # write bytes to read
        sizeb = size.to_bytes(1, 'big')
        crc = reduce(lambda x, y: x ^ y, sizeb, 0xff).to_bytes(1, 'big')
        # write number of bytes to read
        self.ser.write(sizeb)
        self.ser.write(crc)
        if self.check_ack() == 0:
            return -6, b''

        #time.sleep(0.01)
        t = random.uniform(0.01, 0.5) # DEBUG
        time.sleep(t)

        # read memory
        #mem = self.ser.read(size)
        mem = self.ser.read(1024) # DEBUG
        return 0, mem

    # Dumps the whole memory to a file.
    # Keeps track of the current address and dump length.
    # response = -4: no successful read, last read yielded RDP active.
    # response = -5: no successful read, error during writing memory address.
    # response = -6: no successful read, error during writing number of bytes to read.
    # response = -7: if at least one read attempt was successful, however, memory read yielded invalid results.
    # response = 0: if at least one read was successful.
    # response = 1: Memory dump complete.
    def dump_memory_to_file(self, dump_filename):
        successes = 0
        read_sucesses = 0
        response = 0
        fails = 0
        last_response = 0
        while True:
            # setup bootloader communication, this function triggers the glitch
            # returns -4 if RDP is active.
            response = self.setup_memread()
            if response != 0:
                break

            # read memory if RDP is inactive
            mem = b""
            len_to_dump = 0xFF if (self.current_dump_len // 0xFF) else self.current_dump_len % 0xFF
            response, mem = self.read_memory(self.current_dump_addr, len_to_dump)
            last_response = response
            if response == 0:
                # response successful, however, memory read may still yield invalid results
                successes += 1
                if response == 0 and len(mem) == (len_to_dump + 1) and mem != b"\x00" * (len_to_dump + 1):
                    read_sucesses += 1
                    with open(dump_filename, 'ab+') as f:
                        f.write(mem)
                    self.current_dump_len -= len(mem)
                    print(f"[+] Dumped 0x{len(mem):x} bytes from addr 0x{self.current_dump_addr:x}, {self.current_dump_len:x} bytes left")
                    self.current_dump_addr += len(mem)
            else:
                fails += 1
                print("[-] Memory dump failed.")

            if self.current_dump_len <= 0:
                print("[+] Dump finished.")
                return 1

            if successes > 20 and read_sucesses == 0:
                print("[-] Something went wrong. Break.")
                break

        if fails > 0:
            response = last_response
        if successes > 0:
            response = -7
        if read_sucesses > 0:
            response = 0

        return response

    def __del__(self):
        print("[+] Closing serial port.")
        self.ser.close()

if __name__ == "__main__":
    com = BootloaderCom(port=sys.argv[1])
    ret = com.init_get_id()
    print(ret)
    if ret != 0:
        sys.exit(1)

    ret = com.setup_memread()
    print(ret)
    if ret != 0:
        sys.exit(1)

    start = 0x08000000
    size  = 0xff
    ret, mem = com.read_memory(start, size)
    print(ret)
    if ret == 0:
        print(mem)
    sys.exit(1)