#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import serial
from functools import reduce
import sys
from GlitchState import ErrorType, WarningType, OKType, ExpectedType, SuccessType
import time

class _Expected(ExpectedType):
    default = 0
    rdp_active = 1

class _Error(ErrorType):
    default = 0
    nack = 1
    no_response = 2
    bootloader_not_available = 3
    bootloader_error = 4
    id_error = 5

class _Warning(WarningType):
    default = 0
    flash_reset = 1
    timeout = 2

class _OK(OKType):
    default = 0
    ack = 1
    bootloader_ok = 2
    rdp_inactive = 3
    dump_error = 4

class _Success(SuccessType):
    default = 0
    dump_ok = 1
    dump_successful = 2
    dump_finished = 3

class GlitchState():
    Error = _Error
    Warning = _Warning
    OK = _OK
    Expected = _Expected
    Success = _Success

class BootloaderCom:
    NACK = b'\x1f'
    ACK  = b'\x79'
    verbose = False

    def __init__(self, port, dump_address=0x08000000, dump_len=0x400):
        print(f"[+] Opening serial port {port}.")
        self.ser = serial.Serial(port=port, baudrate=115200, timeout=1, bytesize=8, parity="E", stopbits=1)
        # memory read settings
        self.current_dump_addr = dump_address
        self.current_dump_len = dump_len

    def check_ack(self):
        s = self.ser.read(1)
        if s == self.NACK:
            return GlitchState.Error.nack
        elif s == self.ACK:
            return GlitchState.OK.ack
        return GlitchState.Error.no_response

    def flush(self):
        self.ser.reset_output_buffer()
        self.ser.reset_input_buffer()
        # read garbage and discard
        #self.ser.read(1024)

    def init_get_id(self):
        # init bootloader
        self.ser.write(b'\x7f')
        if issubclass(type(self.check_ack()), ErrorType):
            return GlitchState.Error.bootloader_not_available

        # get chip id command (x02: chip id, xfd: crc)
        self.ser.write(b'\x02\xfd')
        if issubclass(type(self.check_ack()), ErrorType):
            return GlitchState.Error.id_error
        
        # read chip id
        s = self.ser.read(3)
        chipid = s[1:3]

        if self.verbose:
            print(f"[+] Chip ID: {chipid}")
        return GlitchState.OK.default

    # returns "bootloader_ok" if bootloader setup was successful (expected)
    # returns "bootloader_error" else
    def init_bootloader(self):
        # init bootloader
        self.ser.write(b'\x7f')
        s = self.ser.read(1)
        if s == self.ACK:
            return GlitchState.OK.bootloader_ok
        return GlitchState.Error.bootloader_error

    # returns "rdp_active" if RDP is active (expected)
    # returns "rdp_inactive" if glitch was successful
    def setup_memread(self):
        # read memory (x11: read memory, xee: crc)
        self.ser.write(b'\x11\xee')
        s = self.ser.read(1)
        if s == self.ACK:
            return GlitchState.OK.rdp_inactive
        return GlitchState.Expected.rdp_active

    # returns "dump_ok" if glitch and memory read was successful
    # returns "dump_error" if glitch was successful, however memory read yielded eroneous results
    # must be used in combination with setup_memread
    def read_memory(self, start, size):
        # write memory address
        startb = start.to_bytes(4, 'big')
        crc = reduce(lambda x, y: x ^ y, startb, 0).to_bytes(1, 'big')
        self.ser.write(startb)
        self.ser.write(crc)
        self.ser.read(1)

        # write bytes to read
        sizeb = size.to_bytes(1, 'big')
        crc = reduce(lambda x, y: x ^ y, sizeb, 0xff).to_bytes(1, 'big')
        # write number of bytes to read
        self.ser.write(sizeb)
        self.ser.write(crc)
        self.ser.read(1)

        # read memory
        mem = self.ser.read(size)

        print(f"[+] Length of memory dump: {len(mem)}")
        print(f"[+] Content: {mem}")
        response = GlitchState.OK.default
        if len(mem) == 255 and mem != b"\x00" * 255:
            response = GlitchState.Success.dump_ok
        else:
            response = GlitchState.OK.dump_error
        return response, mem

    # returns "rdp_active" if RDP is active (expected)
    # returns "rdp_inactive" if glitch was successful
    # returns "dump_error" if glitch was successful but dumped memory was eroneous
    # returns "dump_ok" if glitch was successful and dumped memory was good
    def dump_memory_debug(self):
        # read memory (x11: read memory, xee: crc)
        self.ser.write(b'\x11\xee')
        s = self.ser.read(1)

        mem = b''
        if s == self.ACK:
            # write memory address
            self.ser.write(b'\x08\x00\x00\x00\x08')
            self.ser.read(1)
            # write number of bytes to read
            self.ser.write(b'\xff\x00')
            self.ser.read(1)

            # read memory
            mem = self.ser.read(255)

            if mem != b'\x1f' and mem != b'\x79' and mem != b'':
                print(f"[+] Length of memory dump: {len(mem)}")
                print(f"[+] Content: {mem}")
                time.sleep(5)
                return GlitchState.Success.dump_ok, mem
            else:
                time.sleep(5)
                return GlitchState.OK.dump_error, mem

        if s == self.ACK:
            return GlitchState.OK.rdp_inactive, mem

        return GlitchState.Expected.rdp_active, mem

    # returns "dump_ok" if glitch and memory read was successful
    # returns "dump_error" if glitch was successful, however memory read yielded eroneous results
    # must be used in combination with setup_memread
    def read_memory_debug(self, start, size):
        # write memory address
        self.ser.write(b'\x08\x00\x00\x00\x08')
        self.ser.read(1)
        # write number of bytes to read
        self.ser.write(b'\xff\x00')
        self.ser.read(1)

        # read memory
        mem = self.ser.read(size)

        print(f"[+] Length of memory dump: {len(mem)}")
        print(f"[+] Content: {mem}")
        response = GlitchState.OK.default
        if len(mem) == 255 and mem != b"\x00" * 255:
            response = GlitchState.Success.dump_ok
        else:
            response = GlitchState.OK.dump_error
        return response, mem

    # returns "error" if memory read was eroneous
    # returns "dump_successful" if one dump was successful
    # returns "dump_finished" if entire memory was dummped
    def dump_memory_to_file(self, dump_filename):
        # read memory if RDP is inactive
        len_to_dump = 0xFF if (self.current_dump_len // 0xFF) else self.current_dump_len % 0xFF
        response, mem = self.read_memory(self.current_dump_addr, len_to_dump)

        if issubclass(type(response), ErrorType) or response == GlitchState.OK.dump_error:
            return response, mem

        # write memory dump to file
        with open(dump_filename, 'ab+') as f:
            f.write(mem)
        self.current_dump_len -= len(mem)
        print(f"[+] Dumped 0x{len(mem):x} bytes from addr 0x{self.current_dump_addr:x}, {self.current_dump_len:x} bytes left")
        self.current_dump_addr += len(mem)

        if self.current_dump_len <= 0:
            print("[+] Dump finished.")
            return GlitchState.Success.dump_finished, mem
        return GlitchState.Success.dump_successful, mem

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