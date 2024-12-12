#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import serial
from functools import reduce
import sys
from .GlitchState import ErrorType, WarningType, OKType, ExpectedType, SuccessType
import time

class _Expected(ExpectedType):
    """
    Enum class for expected states.
    """
    default = 0
    rdp_active = 1

class _Error(ErrorType):
    """
    Enum class for error states.
    """
    default = 0
    nack = 1
    no_response = 2
    bootloader_not_available = 3
    bootloader_error = 4
    id_error = 5

class _Warning(WarningType):
    """
    Enum class for warning states.
    """
    default = 0
    flash_reset = 1
    timeout = 2

class _OK(OKType):
    """
    Enum class for ok states (no errors).
    """
    default = 0
    ack = 1
    bootloader_ok = 2
    rdp_inactive = 3
    dump_error = 4

class _Success(SuccessType):
    """
    Enum class for success states (glitching was successful).
    """
    default = 0
    dump_ok = 1
    dump_successful = 2
    dump_finished = 3

class GlitchState():
    """
    Class that combines subclasses for different states. Can be used to classify different responses.

    - Error: Enum class for error states.
    - Warning: Enum class for warning states.
    - OK: Enum class for ok states (no errors).
    - Expected: Enum class for expected states.
    - Success: Enum class for success states (glitching was successful).

    Example usage:

        from findus.BootloaderCom import GlitchState
        from findus.GlitchState import OKType

        def return_ok():
            return GlitchState.OK.ack

        def main():
            response = return_ok()
            if issubclass(type(response), OKType):
                print("Response was OK.")
    """
    Error = _Error
    Warning = _Warning
    OK = _OK
    Expected = _Expected
    Success = _Success

class BootloaderCom:
    """
    Class that contains methods to communicate with STM32 processors in bootloader mode.
    Example usage:
    
        from findus.BootloaderCom import BootloaderCom
        bootcom = BootloaderCom(port="/dev/ttyACM1")
        response = bootcom.init_bootloader()
        response = bootcom.setup_memread()
        response, mem = self.bootcom.read_memory(0x08000000, 0xFF)

    Methods:
        __init__: Default constructor.
        check_ack: Returns GlitchState.Error.nack or GlitchState.Error.ack depending on the bootloader response.
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

    def check_ack(self) -> GlitchState:
        r"""
        Read a byte from serial and returns `GlitchState.Error.nack` or `GlitchState.Error.ack` depending whether the device's bootloader responds with a NACK or a ACK over UART.

        Returns:
            Returns `GlitchState.Error.nack` if `b'\\x1f'` was received, or `GlitchState.Error.ack` if `b'\\x79'` was received. If the target did not respond, a `GlitchState.Error.no_response` is returned.
        """
        s = self.ser.read(1)
        if s == self.NACK:
            return GlitchState.Error.nack
        elif s == self.ACK:
            return GlitchState.OK.ack
        return GlitchState.Error.no_response

    def flush(self):
        """
        Flush the serial data buffers.
        """
        self.ser.reset_output_buffer()
        self.ser.reset_input_buffer()
        # read garbage and discard
        #self.ser.read(1024)

    # returns "bootloader_not_available" if bootloader is unavailable
    # returns "id_error" if reading from bootloader was not successful
    # returns "default" else
    def init_get_id(self) -> GlitchState:
        """
        Initializes the bootloader communication and asks the chip for its ID.
        
        Returns:
            Returns `GlitchState.Error.bootloader_not_available` if the bootloader is unavailable, `GlitchState.Error.id_error` if 'id command' was not successful, and `GlitchState.OK.default` if successful.
        """
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
    def init_bootloader(self) -> GlitchState:
        """
        Initializes the bootloader communication via UART.
        
        Returns:
            Returns `GlitchState.OK.bootloader_ok` if bootloader setup was successful (expected), returns `GlitchState.Error.bootloader_error` else.
        """
        # init bootloader
        self.ser.write(b'\x7f')
        s = self.ser.read(1)
        if s == self.ACK:
            return GlitchState.OK.bootloader_ok
        return GlitchState.Error.bootloader_error

    # returns "rdp_active" if RDP is active (expected)
    # returns "rdp_inactive" if glitch was successful
    def setup_memread(self, read:bool = True) -> GlitchState:
        """
        Configures the bootloader to read memory from specific memory addresses.

        Parameters:
            read: Whether to read the response or not.

        Returns:
            Returns `GlitchState.Expected.rdp_active` if RDP is active (expected), or `GlitchState.OK.rdp_inactive` if glitch was successful
        """
        # read memory (x11: read memory, xee: crc)
        self.ser.write(b'\x11\xee')
        if read:
            s = self.ser.read(1)
            if s == self.ACK:
                return GlitchState.OK.rdp_inactive
        return GlitchState.Expected.rdp_active

    # returns "dump_ok" if glitch and memory read was successful
    # returns "dump_error" if glitch was successful, however memory read yielded eroneous results
    # must be used in combination with setup_memread
    def read_memory(self, start:int, size:int) -> [GlitchState, bytes]:
        """
        Read the memory from a given memory address.
        Must be used in combination with `setup_memread`.

        Parameters:
            start: Memory address to start reading from.
            size: Size of the memory to read from the device.
        Returns:
            Returns `GlitchState.Success.dump_ok` if glitch and memory read was successful, or `GlitchState.OK.dump_error` if glitch was successful, however memory read yielded eroneous results.
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
    def dump_memory_debug(self) -> [GlitchState, bytes]:
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
    def read_memory_debug(self, start:int, size:int) -> [GlitchState, bytes]:
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
    def dump_memory_to_file(self, dump_filename:str) -> [GlitchState, bytes]:
        """
        Read the memory from a given memory range and write the memory dump to a file.
        
        Parameters:
            dump_filename: Filename to write the memory dump to.
        Returns:
            Returns `GlitchState.OK.dump_error` if memory read was eroneous, `GlitchState.Success.dump_successful` if one dump was successful, and `GlitchState.Success.dump_finished` if entire memory was dummped.
        """
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
        """
        Default deconstructor. Closes the serial communication to the bootloader.
        """
        print("[+] Closing serial port.")
        self.ser.close()

def main(argv=sys.argv):
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

if __name__ == "__main__":
    main()