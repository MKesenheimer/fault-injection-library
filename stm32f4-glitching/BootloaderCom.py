# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import serial
import time
from functools import reduce
import sys

class BootloaderCom:
    NACK = b'\x1f'
    ACK  = b'\x79'
    verbose = False

    def __init__(self, serial):
        self.ser = serial

    def check_ack(self):
        s = self.ser.read(1)
        if s != self.ACK:
            #print(s)
            return 0
        return 1

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

    def setup_memread(self):
        # read memory (x11: read memory, xee: crc)
        self.ser.write(b'\x11\xee')

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

        time.sleep(0.01)

        # get memory
        mem = self.ser.read(size)
        return 0, mem

    def __del__(self):
        print("[+] Closing serial port.")
        self.ser.close()

if __name__ == "__main__":
    ser = serial.Serial(port="/dev/tty.usbserial-21101", baudrate=115200, timeout=0.25, bytesize=8, parity='E', stopbits=1)

    com = BootloaderCom(ser)
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