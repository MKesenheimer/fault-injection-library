#!/usr/bin/env python3
# Copyright (C) 2025 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# programming
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x unlock 0; exit"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; program toggle-led-STM32L0.elf; reset run; exit;"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x lock 0; exit"
# -> power cycle the target!

# reading
# >  openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; dump_image dump.bin 0x08000000 0x400; exit"

# debugging (install arm-none-eabi-gdb!)
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init"
# > arm-none-eabi-gdb read-out-protection-test-STM32L0.elf
# (gdb) target extended-remote localhost:3333
# (gdb) x 0x08000000
## or
# > telnet localhost 4444
# > mdw 0x08000000

# load image to ram
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; load_image rdp-downgrade-STM32L0.elf" -c "reg sp 0x20000000" -c "reg pc 0x20000004" -c "resume; exit"

# load image to ram and execute
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; load_image rdp-downgrade-STM32L0.elf" -c "reg sp 0x20002000" -c "reg pc 0x20000fa4" -c "resume" -c "exit"

# Alternatively load with gdb:
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt"
# > arm-none-eabi-gdb rdp-downgrade-STM32L0.elf
# > target remote :3333
# > load rdp-downgrade-STM32L0.elf
## Start address 0x20000fa4, load size 4764
# > x $pc
## 0x20000fa4 <Reset_Handler>:	0x4685480d
# > b *0x20000fa4
# > continue
# > x $sp
## 0x20001ff8

# read RDP level
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init" -c "mdw 0x4002201c" -c "exit"


import time
import subprocess
import re
import socket

class DebugInterface():
    def __init__(self, interface:str = "stlink", interface_config:str=None, target:str = "stm32l0", target_config:str=None, transport:str = "hla_swd", gdb_exec:str = "arm-none-eabi-gdb", adapter_serial:str = None, gdb_port = 3333, telnet_port = 4444, tcl_port = 6666):
        self.openocd_process = None
        self.gdb_process = None
        self.target_name = target
        self.socket = None
        self.gdb_exec = gdb_exec
        self.transport = transport
        self.adapter_serial = adapter_serial
        self.gdb_port = gdb_port
        self.telnet_port = telnet_port
        self.tcl_port = tcl_port
        if interface_config is None:
            self.interface_config = f'interface/{interface}.cfg'
        else:
            self.interface_config = interface_config
        if target_config is None:
            self.target_config = f'target/{self.target_name}.cfg'
        else:
            self.target_config = target_config

    def program_target(self, glitcher, elf_image:str = "program.elf", unlock:bool = True, rdp_level:int = 0, power_cycle_time:float = 0.1, verbose:bool = False):
        """
        TODO
        """
        if unlock:
            glitcher.reset(0.01)
            time.sleep(0.005)
            self.unlock_target(verbose)
            glitcher.power_cycle_reset(power_cycle_time)
            time.sleep(power_cycle_time)
        self.write_image(elf_image=elf_image)
        if rdp_level == 1:
            self.lock_target(verbose)
            # changes in the RDP level become active after a power-cycle
            glitcher.power_cycle_reset(power_cycle_time)
            time.sleep(power_cycle_time)

    def unlock_target(self, verbose:bool = False):
        """
        Unlock the target and remove any read-out protection.
        Attention: This will erase the targets flash!
        """
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', f'init; halt; {self.target_name}x unlock 0; exit'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        if verbose:
            print(result.stdout + result.stderr)

    def lock_target(self, verbose:bool = False):
        """
        TODO
        """
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', f'init; halt; {self.target_name}x lock 0; exit'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        if verbose:
            print(result.stdout + result.stderr)

    def write_image(self, elf_image:str = "program.elf", verbose:bool = False):
        """
        Write image to flash.
        """
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', f'init; halt; program {elf_image}; exit'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        if verbose:
            print(result.stdout + result.stderr)

    def load_exec(self, elf_image:str = "program.elf", sp:int = 0x20002000, pc:int = 0x20000fa4, verbose:bool = False):
        """
        Load image to RAM and execute.
        Attention: Program must also be compiled to be compatible to run in RAM.
        """
        # openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; load_image rdp-downgrade-STM32L0.elf" -c "reg sp 0x20002000" -c "reg pc 0x20000fa4" -c "resume" -c "exit"
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', f'init; halt; load_image {elf_image}',
            '-c', f'reg sp {hex(sp)}',
            '-c', f'reg pc {hex(pc)}',
            '-c', 'resume',
            '-c', 'exit',
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        if verbose:
            print(result.stdout + result.stderr)

    def read_image(self, bin_image:str = "memory_dump.bin", start_addr:int = 0x08000000, length:int = 0x400, verbose:bool = False):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', f'init; dump_image {bin_image} {hex(start_addr)} {hex(length)}; exit'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        if verbose:
            print(result.stdout + result.stderr)

    def test_connection(self):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', 'init; reset run; exit'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        print(result.stdout + result.stderr)

    def read_address(self, address):
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', 'init',
            '-c', f'mdw {hex(address)}',
            '-c', 'exit'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        result = subprocess.run(args, text=True, capture_output=True)
        response = result.stdout + result.stderr
        return self.extract_memory_content(response=response, address=address), response

    def read_option_bytes(self):
        mem, response = self.read_address(0x4002201c)
        if mem is not None:
            return mem, response
        return 0x00, response

    def read_pcrop(self):
        optbytes, _ = self.read_option_bytes()
        pcrop = (optbytes & 0x100) >> 8
        return pcrop

    def read_rdp(self):
        optbytes, _ = self.read_option_bytes()
        rdp = (optbytes & 0xff)
        return rdp

    def read_rdp_and_pgrop(self, verbose:bool = False):
        optbytes, response = self.read_option_bytes()
        if verbose:
            print(response)
        pcrop = (optbytes & 0x100) >> 8
        rdp = (optbytes & 0xff)
        return rdp, pcrop

    def kill_process(self, port:int, verbose=False):
        # Find process using the port
        cmd = ["lsof", "-i", f":{port}"]
        #pattern = r"\b(\d+)\b"  # Regex for PID
        pattern = r"openocd\s+(\d+)"  # Regex for PID
        # Run command and search for PID
        # trunk-ignore(bandit/B603)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if verbose:
            print(result)
        matches = re.findall(pattern, result.stdout)
        if matches:
            pid = matches[-1]  # Get the last match (PID)
            print(f"[+] Found process {pid} using port {port}")
            # Kill the process
            try:
                # trunk-ignore(bandit/B607)
                # trunk-ignore(bandit/B603)
                subprocess.run(["kill", "-9", pid], check=True)
                print(f"[+] Process {pid} killed successfully.")
            except Exception as e:
                print(f"[-] Error killing process: {e}")

    def attach(self, delay=0.1):
        # check if there is a dangling process that would interfere with openocd
        self.kill_process(self.gdb_port)
        # trunk-ignore(bandit/B607)
        # trunk-ignore(bandit/B603)
        args = [
            'openocd',
            '-f', self.interface_config,
            '-c', f'transport select {self.transport}',
            '-f', self.target_config,
            '-c', f'gdb_port {self.gdb_port}',
            '-c', f'telnet_port {self.telnet_port}',
            '-c', f'tcl_port {self.tcl_port}',
            '-c', 'init'
            ]
        if self.adapter_serial is not None:
            args.insert(3, '-c')
            args.insert(4, f'adapter serial {self.adapter_serial}')
        self.openocd_process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
        time.sleep(delay)

    def detach(self):
        if self.openocd_process is not None:
            self.openocd_process.terminate()
            self.openocd_process.wait()
            self.openocd_process = None
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        if self.gdb_process is not None:
            self.gdb_process.terminate()
            self.gdb_process = None

    def gdb_load_exec(self, elf_image:str = "program.elf", timeout=0.3, verbose=False):
        # trunk-ignore(bandit/B603)
        self.gdb_process = subprocess.Popen([
            f'{self.gdb_exec}',
            '--interpreter=mi2',
            f'{elf_image}'
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.gdb_process.stdin.write(f"target remote localhost:{self.gdb_port}\n")
        self.gdb_process.stdin.write(f"load {elf_image}\n")
        self.gdb_process.stdin.write("continue\n")
        self.gdb_process.stdin.write("detach\n")
        self.gdb_process.stdin.write("quit\n")
        self.gdb_process.stdin.flush()
        output, error = "", ""
        try:
            output, error = self.gdb_process.communicate(timeout=timeout)
        except Exception as e:
            #print(f"[-] Exception in DebugInterface:gdb_load_exec occured:\n{e}")
            pass
        finally:
            if verbose:
                print(output)
                print(error)
        self.gdb_process.terminate()

    def telnet_init(self):
        # generate a connection to the openocd telnet server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)
        self.socket.connect(('localhost', {self.telnet_port}))
        # receive start messages
        time.sleep(0.1)
        self.socket.recv(4096)

    def telnet_interact(self, command:str, wait_time:float = 0.01, verbose:bool = False):
        if self.openocd_process is None or self.socket is None:
            self.telnet_init()
        command += "\n"
        self.socket.sendall(command.encode("utf-8"))
        time.sleep(wait_time)
        response = self.socket.recv(4096)
        if verbose:
            print(response.decode("utf-8"))
        return response.decode("utf-8")

    def telnet_read_address(self, address:int):
        command = f"mdw {hex(address)}"
        response = self.telnet_interact(command)
        if "Previous state query failed, trying to reconnect" in response:
            response += self.telnet_interact(command)
        return self.extract_memory_content(response=response, address=address), response

    def telnet_read_image(self, bin_image:str = "memory_dump.bin", start_addr:int = 0x08000000, length:int = 0x400, verbose:bool = False):
        command = f"init; dump_image {bin_image} {hex(start_addr)} {hex(length)}; exit"
        response = self.telnet_interact(command)
        if verbose:
            print(response)

    def extract_memory_content(self, response:str, address:int = 0x00):
        if "Error: Failed to read memory at" not in response:
            match = re.search(fr'{hex(address)[2:]}:\s*([0-9A-Fa-f]+)', response)
            if match:
                return int(match.group(1), 16)
            else:
                return None

    def characterize(self, response:str, mem:int):
        # possibly ok
        if mem is not None:
            if mem != 0x00:
                return b'success: RDP inactive'
            else:
                return b'ok: read zero'
        # Error: no connection
        elif "Error: init mode failed (unable to connect to the target)" in response:
            return b'error: no connection'
        # Warning: Polling failed
        elif "Polling target" in response:
            return b'warning: polling failed'
        # Warning: Device lockup
        if "clearing lockup after double fault" in response:
            return b'warning: lock-up'
        # Warning: else
        elif "Warning" in response:
            return b'warning: default warning'
        # expected state
        elif "Error: Failed to read memory at" in response:
            return b'expected: RDP active'
        # no response
        return b'error: no response'

    def __del__(self):
        print("[+] Detaching debugger.")
        self.detach()