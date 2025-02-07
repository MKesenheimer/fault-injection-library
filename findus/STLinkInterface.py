#!/usr/bin/env python3
# Copyright (C) 2025 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# programming
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x unlock 0; exit"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; program read-out-protection-test-CW308_STM32L0.elf verify reset exit;"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x lock 0; sleep 1000; reset run; shutdown"
# -> power cycle the target!

# reading
# >  openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; dump_image dump.bin 0x08000000 0x400; exit"

# debugging (install arm-none-eabi-gdb!)
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init"
# > arm-none-eabi-gdb read-out-protection-test-CW308_STM32L0.elf
# (gdb) target extended-remote localhost:3333
# (gdb) x 0x08000000
## or
# > telnet localhost 4444
# > mdw 0x08000000

import time
import subprocess
import re
import socket

from .GlitchState import ErrorType, WarningType, OKType, ExpectedType, SuccessType

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

        from findus.STLinkInterface import STLinkInterface, GlitchState
        from findus.GlitchState import OKType, ExpectedType

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

class STLinkInterface():
    def __init__(self, processor:str = "stm32l0"):
        self.process = None
        self.processor_name = processor
        self.socket = None

    def program_target(self, glitcher, elf_image:str = "program.elf", rdp_level:int = 0):
        glitcher.reset(0.01)
        time.sleep(0.005)
        self.unlock_target()
        glitcher.power_cycle_target()
        time.sleep(0.1)
        self.write_image(elf_image=elf_image)
        if rdp_level == 1:
            self.lock_target()
        glitcher.power_cycle_target()
        time.sleep(0.1)

    def unlock_target(self):
        """
        Unlock the target and remove any read-out protection.
        Attention: This will erase the targets flash!
        """
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        result = subprocess.run([
            'openocd',
            '-f', 'interface/stlink.cfg',
            '-c', 'transport select hla_swd',
            '-f', f'target/{self.processor_name}.cfg',
            '-c', f'init; halt; {self.processor_name}x unlock 0; exit'
            ], text=True, capture_output=True)
        print(result.stdout)
        print(result.stderr)

    def lock_target(self):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        result = subprocess.run([
            'openocd',
            '-f', 'interface/stlink.cfg',
            '-c', 'transport select hla_swd',
            '-f', f'target/{self.processor_name}.cfg',
            '-c', f'init; halt; {self.processor_name}x lock 0; sleep 1000; reset run; shutdown;'
            ], text=True, capture_output=True)
        print(result.stdout)
        print(result.stderr)

    def write_image(self, elf_image:str = "program.elf"):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        result = subprocess.run([
            'openocd',
            '-f', 'interface/stlink.cfg',
            '-c', 'transport select hla_swd',
            '-f', f'target/{self.processor_name}.cfg',
            '-c', f'init; halt; program {elf_image} verify reset exit;'
            ], text=True, capture_output=True)
        print(result.stdout)
        print(result.stderr)

    def read_image(self, bin_image:str = "memory_dump.bin", start_addr:int = 0x08000000, length:int = 0x400):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        result = subprocess.run([
            'openocd',
            '-f', 'interface/stlink.cfg',
            '-c', 'transport select hla_swd',
            '-f', f'target/{self.processor_name}.cfg',
            '-c', f'init; dump_image {bin_image} {hex(start_addr)} {hex(length)}; exit'
            ], text=True, capture_output=True)
        print(result.stdout)
        print(result.stderr)

    def read_address(self, address:int):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        result = subprocess.run([
            'openocd',
            '-f', 'interface/stlink.cfg',
            '-c', 'transport select hla_swd',
            '-f', f'target/{self.processor_name}.cfg',
            '-c', 'init',
            '-c', f'mdw {hex(address)}',
            '-c', 'exit'
            ], text=True, capture_output=True)
        response = result.stdout + result.stderr
        #print(response)
        match = re.search(fr'{hex(address)[2:]}:\s*([0-9A-Fa-f]+)', response)
        if match:
            if match.group(1) != "00000000":
                return GlitchState.OK.rdp_inactive, match.group(1)
            else:
                return GlitchState.Expected.rdp_active, None
        return GlitchState.Error.no_response, None

    def attach(self):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        self.process = subprocess.Popen([
            'openocd',
            '-f', 'interface/stlink.cfg',
            '-c', 'transport select hla_swd',
            '-f', f'target/{self.processor_name}.cfg',
            '-c', 'init'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)

        # generate a connection to the openocd telnet server
        time.sleep(1)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)
        self.socket.connect(('localhost', 4444))
        # receive start messages
        time.sleep(0.001)
        self.socket.recv(4096)

    def detach(self):
        if self.process is not None:
            self.process.terminate()
            self.process = None
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def telnet_interact(self, command:str):
        command += "\n"
        self.socket.sendall(command.encode("utf-8"))
        time.sleep(0.01)
        response = self.socket.recv(4096)
        return response.decode("utf-8")

    def telnet_read_address(self, address:int):
        command = f"mdw {hex(address)}"
        response = self.telnet_interact(command)
        #print(response)
        match = re.search(fr'{hex(address)[2:]}:\s*([0-9A-Fa-f]+)', response)
        if match:
            if match.group(1) != "00000000":
                return GlitchState.OK.rdp_inactive, match.group(1)
            else:
                return GlitchState.Expected.rdp_active, None
        return GlitchState.Error.no_response, None

    def telnet_read_image(self, bin_image:str = "memory_dump.bin", start_addr:int = 0x08000000, length:int = 0x400):
        command = f"init; dump_image {bin_image} {hex(start_addr)} {hex(length)}; exit"
        response = self.telnet_interact(command)
        print(response)
        #return response

    def __del__(self):
        print("[+] Detaching debugger.")
        self.detach()