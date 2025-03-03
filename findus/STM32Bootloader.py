#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import serial
from functools import reduce
import sys
import time

class STM32Bootloader:
    """
    Class that contains methods to communicate with STM32 processors in bootloader mode.
    Example usage:
    
        from findus.STM32Bootloader import STM32Bootloader
        bootcom = STM32Bootloader(port="/dev/ttyACM1")
        response = bootcom.init_bootloader()
        response = bootcom.setup_memread()
        response, mem = self.bootcom.read_memory(0x08000000, 0xFF)

    Methods:
        __init__: Default constructor.
        check_ack: Returns b'error: NACK' or b'ok: ACK' depending on the bootloader response.
        flush: Flush the serial buffers.
        init_get_id: Initializes the bootloader communication and asks the chip for its ID.
        init_bootloader: Initializes the bootloader communication via UART.
        setup_memread: Configures the bootloader to read memory from specific memory addresses.
        read_memory: Read the memory from a given memory address.
        dump_memory_to_file: Read the memory from a given memory range and write to file.
        __del__: Default deconstructor. Closes the serial communication to the bootloader.
    """
    NACK = b'\x1f'
    ACK  = b'\x79'
    verbose = False

    def __init__(self, port:str, dump_address:int=0x08000000, dump_len:int=0x400):
        """
        Default constructor. Initializes the serial connection to the STM32 target (in 8e1 configuration), and stores parameter for the memory dump.
        
        Parameters:
            port: Port identifier of the STM32 target.
            dump_address: Memory address to start reading from.
            dump_len: Size of the memory to read from the device.
        Returns:
            return
        """
        print(f"[+] Opening serial port {port}.")
        self.ser = serial.Serial(port=port, baudrate=115200, timeout=1, bytesize=8, parity="E", stopbits=1)
        # memory read settings
        self.current_dump_addr = dump_address
        self.current_dump_len = dump_len

    def check_ack(self) -> bytes:
        r"""
        Read a byte from serial and returns `b'error: NACK'` or `b'ok: ACK'` depending whether the device's bootloader responds with a NACK or a ACK over UART.

        Returns:
            Returns `b'error: NACK'` if `b'\\x1f'` was received, or `b'ok: ACK'` if `b'\\x79'` was received. If the target did not respond, a `b'error: no response'` is returned.
        """
        s = self.ser.read(1)
        if s == self.NACK:
            return b'error: NACK'
        elif s == self.ACK:
            return b'ok: ACK'
        return b'error: no response'

    def flush(self):
        """
        Flush the serial data buffers.
        """
        self.ser.reset_output_buffer()
        self.ser.reset_input_buffer()
        # read garbage and discard
        #self.ser.read(1024)

    # returns b'error: bootloader not available' if bootloader is unavailable
    # returns b'error: id command error' if reading from bootloader was not successful
    # returns b'ok' else
    def init_get_id(self) -> bytes:
        """
        Initializes the bootloader communication and asks the chip for its ID.
        
        Returns:
            Returns `b'error: bootloader not available'` if the bootloader is unavailable, `b'error: id command error'` if 'id command' was not successful, and `b'ok'` if successful.
        """
        # init bootloader
        self.ser.write(b'\x7f')
        if b'error' in self.check_ack():
            return b'error: bootloader not available'

        # get chip id command (x02: chip id, xfd: crc)
        self.ser.write(b'\x02\xfd')
        if b'error' in self.check_ack():
            return b'error: id command error'
        
        # read chip id
        s = self.ser.read(3)
        chipid = s[1:3]

        if self.verbose:
            print(f"[+] Chip ID: {chipid}")
        return b'ok'

    # returns b'ok: bootloader ok' if bootloader setup was successful (expected)
    # returns b'error: bootloader error' else
    def init_bootloader(self) -> bytes:
        """
        Initializes the bootloader communication via UART.
        
        Returns:
            Returns `b'ok: bootloader ok'` if bootloader setup was successful (expected), returns `b'error: bootloader error'` else.
        """
        # init bootloader
        self.ser.write(b'\x7f')
        s = self.ser.read(1)
        if s == self.ACK:
            return b'ok: bootloader ok'
        return b'error: bootloader error'

    # returns b'expected: RDP active' if RDP is active (expected)
    # returns b'success: RDP inactive' if glitch was successful
    # returns b'error: no response' else
    def setup_memread(self, read:bool = True) -> bytes:
        """
        Configures the bootloader to read memory from specific memory addresses.

        Parameters:
            read: Whether to read the response or not.

        Returns:
            Returns `b'expected: RDP active'` if RDP is active (expected), or `b'success: RDP inactive'` if glitch was successful
        """
        # read memory command (x11: read memory, xee: crc)
        self.ser.write(b'\x11\xee')
        if read:
            s = self.ser.read(1)
            if s == self.ACK:
                return b'success: RDP inactive'
            elif s == self.NACK:
                return b'expected: RDP active'
        return b'error: no response'

    # returns b'success: dump ok' if glitch and memory read was successful
    # returns b'ok: dump error' if glitch was successful, however memory read yielded eroneous results
    # must be used in combination with setup_memread
    def read_memory(self, start:int, size:int) -> [bytes, bytes]:
        """
        Read the memory from a given memory address.
        Must be used in combination with `setup_memread`.

        Parameters:
            start: Memory address to start reading from.
            size: Size of the memory to read from the device.
        Returns:
            Returns `b'success: dump ok'` if glitch and memory read was successful, or `b'ok: dump error'` if glitch was successful, however memory read yielded eroneous results.
        """
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
        response = b'ok'
        if len(mem) == 255 and mem != b"\x00" * 255:
            response = b'success: dump ok'
        else:
            response = b'ok: dump error'
        return response, mem

    # returns b'expected: RDP active' if RDP is active (expected)
    # returns b'success: RDP inactive' if glitch was successful
    # returns b'ok: dump error' if glitch was successful but dumped memory was eroneous
    # returns b'success: dump ok' if glitch was successful and dumped memory was good
    def dump_memory_debug(self) -> [bytes, bytes]:
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
                return b'success: dump ok', mem
            else:
                time.sleep(5)
                return b'ok: dump error', mem

        if s == self.ACK:
            return b'success: RDP inactive', mem

        return b'expected: RDP active', mem

    # returns b'success: dump ok' if glitch and memory read was successful
    # returns b'ok: dump error' if glitch was successful, however memory read yielded eroneous results
    # must be used in combination with setup_memread
    def read_memory_debug(self, start:int, size:int) -> [bytes, bytes]:
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
        response = b'ok'
        if len(mem) == 255 and mem != b"\x00" * 255:
            response = b'success: dump ok'
        else:
            response = b'ok: dump error'
        return response, mem

    # returns b'error: eroneous memory read' if memory read was eroneous
    # returns b'success: dump successful' if one dump was successful
    # returns b'success: dump finished' if entire memory was dummped
    def dump_memory_to_file(self, dump_filename:str) -> [bytes, bytes]:
        """
        Read the memory from a given memory range and write the memory dump to a file.
        
        Parameters:
            dump_filename: Filename to write the memory dump to.
        Returns:
            Returns `b'ok: dump error'` if memory read was eroneous, `b'success: dump successful'` if one dump was successful, and `b'success: dump finished'` if entire memory was dummped.
        """
        # read memory if RDP is inactive
        len_to_dump = 0xFF if (self.current_dump_len // 0xFF) else self.current_dump_len % 0xFF
        response, mem = self.read_memory(self.current_dump_addr, len_to_dump)

        if b'error' in response or response == b'ok: dump error':
            return b'error: eroneous memory read', mem

        # write memory dump to file
        with open(dump_filename, 'ab+') as f:
            f.write(mem)
        self.current_dump_len -= len(mem)
        print(f"[+] Dumped 0x{len(mem):x} bytes from addr 0x{self.current_dump_addr:x}, {self.current_dump_len:x} bytes left")
        self.current_dump_addr += len(mem)

        if self.current_dump_len <= 0:
            print("[+] Dump finished.")
            return b'success: dump finished', mem
        return b'success: dump successful', mem

    def __del__(self):
        """
        Default deconstructor. Closes the serial communication to the bootloader.
        """
        print("[+] Closing serial port.")
        self.ser.close()

def main(argv=sys.argv):
    com = STM32Bootloader(port=sys.argv[1])
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

if __name__ == "__main__":
    main()