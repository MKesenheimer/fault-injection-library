#!/usr/bin/env python3
# Copyright (C) 2025 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

# programming
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x unlock 0; exit"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; program rdp-downgrade-stm32l051.elf; reset run; exit;"
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; stm32l0x lock 0; exit"
# -> power cycle the target!

# reading
# >  openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; dump_image dump.bin 0x08000000 0x400; exit"

# debugging (install arm-none-eabi-gdb!)
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init"
# > arm-none-eabi-gdb rdp-downgrade-stm32l051.elf
# (gdb) target extended-remote localhost:3333
# (gdb) x 0x08000000
## or
# > telnet localhost 4444
# > mdw 0x08000000

# load image to ram
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; load_image rdp-downgrade-stm32l051.elf" -c "reg sp 0x20000000" -c "reg pc 0x20000004" -c "resume; exit"

# load image to ram and execute
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; load_image rdp-downgrade-stm32l051.elf" -c "reg sp 0x20002000" -c "reg pc 0x20000fa4" -c "resume" -c "exit"

# Alternatively load with gdb:
# > openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt"
# > arm-none-eabi-gdb rdp-downgrade-stm32l051.elf
# > target remote :3333
# > load rdp-downgrade-stm32l051.elf
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
    """
    Class to interact with the target device using OpenOCD and GDB.
    """
    def __init__(self, interface:str = "stlink", interface_config:str=None, target:str = "stm32l0", target_config:str=None, transport:str = "hla_swd", gdb_exec:str = "arm-none-eabi-gdb", adapter_serial:str = None, gdb_port = 3333, telnet_port = 4444, tcl_port = 6666):
        """
        Initializes the OpenOCD configuration with default values or custom values provided.
    
        Parameters:
            interface: The interface type, e.g., 'stlink' or 'j-link'. Defaults to 'stlink'.
            interface_config: Path to a custom interface configuration file. If None, uses the default configuration for the specified interface.
            target: The target microcontroller, e.g., 'stm32l0'. Defaults to 'stm32l0'.
            target_config: Path to a custom target configuration file. If None, uses the default configuration for the specified target.
            transport: The transport protocol, e.g., 'hla_swd'. Defaults to 'hla_swd'.
            gdb_exec: The path to the GDB executable. Defaults to 'arm-none-eabi-gdb'.
            adapter_serial: The serial number of the adapter. If None, no specific serial is used.
            gdb_port: The port number for GDB communication. Defaults to 3333.
            telnet_port: The port number for Telnet communication. Defaults to 4444.
            tcl_port: The port number for TCL communication. Defaults to 6666.
        """
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
        Main function to program the target. Optionally unlocks the target, writes the ELF image, and adjusts the RDP level.
        
        Parameters:
            glitcher: An instance of the Glitcher class used for glitching operations.
            elf_image: The path to the ELF image file to be written to the target. Default is "program.elf".
            unlock: Whether to unlock the target before programming. Default is True.
            rdp_level: The desired RDP level (0 or 1). Default is 0.
            power_cycle_time: The time to wait between power cycles. Default is 0.1 seconds.
            verbose: Whether to print verbose output. Default is False.
        """
        if unlock:
            rdp = 0x01
            pcrop = 0x01
            while rdp != 0xaa or pcrop != 0x00:
                glitcher.reset(0.01)
                time.sleep(0.005)
                self.unlock_target(verbose=verbose)
                glitcher.power_cycle_reset(power_cycle_time)
                time.sleep(power_cycle_time)
                rdp, pcrop = self.read_rdp_and_pcrop(verbose=False)
                if verbose:
                    print(f"[+] rdp, pcrop = {hex(rdp)}, {hex(pcrop)}")
        self.write_image(elf_image=elf_image, verbose=verbose)
        rdp, pcrop = self.read_rdp_and_pcrop(verbose=False)
        if verbose:
            print(f"[+] rdp, pcrop = {hex(rdp)}, {hex(pcrop)}")
        if rdp_level == 1:
            self.lock_target(verbose=verbose)
            rdp, pcrop = self.read_rdp_and_pcrop(verbose=False)
            if verbose:
                print(f"[+] rdp, pcrop = {hex(rdp)}, {hex(pcrop)}")
            # changes in the RDP level become active after a power-cycle
            glitcher.power_cycle_reset(power_cycle_time)
            time.sleep(power_cycle_time)

    def unlock_target(self, verbose:bool = False):
        """
        Unlocks the target and removes any read-out protection.
        Attention: This will erase the targets flash!
        """
        if verbose:
            print("[+] Unlocking target...")
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
        Locks the target (activates RDP).
        """
        if verbose:
            print("[+] Locking target...")
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
        Writes an ELF image to the target using OpenOCD.

        Parameters:
            elf_image: The path to the ELF image to be written. Defaults to "program.elf".
            verbose: Whether to print verbose output. Defaults to False.
        """
        if verbose:
            print("[+] Writing image to target...")
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

        Parameters:
            elf_image: The path to the ELF image file to be loaded. Default is "program.elf".
            sp: The initial stack pointer value. Default is 0x20002000.
            pc: The initial program counter value. Default is 0x20000fa4.
            verbose: If True, print the output and error from openocd. Default is False.
        """
        # openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32l0.cfg -c "init; halt; load_image rdp-downgrade-STM32L0.elf" -c "reg sp 0x20002000" -c "reg pc 0x20000fa4" -c "resume" -c "exit"
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
        """
        Reads an image from the target device's memory and saves it to a binary file.
        
        Parameters:
            bin_image: The path to the binary file where the image will be saved.
            start_addr: The starting address in memory to read from.
            length: The number of bytes to read from memory.
            verbose: If True, print the output and error messages.
        """
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
        """
        Tests the connection to the target device by resetting it.
        """
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
        """
        Read memory content from a specific address using OpenOCD.
        
        Parameters:
            address: The memory address to read from.
        
        Returns:
            A tuple containing the extracted memory content and the raw response.
        """
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
        """
        Reads the option bytes from the memory address 0x4002201c.

        Returns:
            A tuple containing the memory value and the response from the read operation.
            If the memory value is None, returns (0x00, response).
        """
        mem, response = self.read_address(0x4002201c)
        if mem is not None:
            return mem, response
        return 0x00, response

    def read_pcrop(self):
        """
        Reads the PCROP (Programmable Code Protection Region) value from the option bytes.

        Returns:
            The PCROP value.
        """
        optbytes, _ = self.read_option_bytes()
        pcrop = (optbytes & 0x100) >> 8
        return pcrop

    def read_rdp(self):
        """
        Reads the RDP (Read Protection) value from the option bytes.

        Returns:
            int: The RDP value.
        """
        optbytes, _ = self.read_option_bytes()
        rdp = (optbytes & 0xff)
        return rdp

    def read_rdp_and_pcrop(self, verbose:bool = False):
        """
        Reads both RDP and PCROP values from the option bytes.

        Parameters:
            verbose: If True, prints the response from the read operation. Defaults to False.

        Returns:
            A tuple containing the RDP and PCROP values.
        """
        optbytes, response = self.read_option_bytes()
        if verbose:
            print(response)
        pcrop = (optbytes & 0x100) >> 8
        rdp = (optbytes & 0xff)
        return rdp, pcrop

    def kill_process(self, port:int, verbose=False):
        """
        Kill the process that is using the specified port.
        
        Parameters:
            port: The port number to check for a process.
            verbose: If True, print detailed output.
        """
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
        """
        Attaches to the OpenOCD server.

        Parameters:
            delay: Delay in seconds before checking if OpenOCD is running.
        """
        # check if there is a dangling process that would interfere with openocd
        self.kill_process(self.gdb_port)
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
        try:
            self.openocd_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            time.sleep(delay)
            if self.openocd_process.poll() is not None:
                out, err = self.openocd_process.communicate()
                raise RuntimeError(f"OpenOCD failed:\n{out}\n{err}")
        except subprocess.TimeoutExpired:
            pass

    def mi_wait_done(self, timeout=1.0, ok_prefixes=("^done", "^running", "^connected"), verbose=False):
        """
        Wait for a GDB MI command to complete with a timeout.
        
        Parameters:
            timeout: Maximum time to wait for the command to complete (default: 1.0 seconds)
            ok_prefixes: Prefixes indicating a successful completion (default: ("^done", "^running", "^connected"))
            verbose: Whether to print each line received (default: False)
        
        Raises:
            TimeoutError: If the command times out
            RuntimeError: If the GDB process exits unexpectedly or encounters an error
        """
        start = time.time()
        while True:
            if time.time() - start > timeout:
                raise TimeoutError("GDB MI command timed out")
            line = self.gdb_process.stdout.readline()
            if not line:
                raise RuntimeError("GDB exited unexpectedly")
            line = line.strip()
            if verbose:
                print(line)
            # Ignore CLI prompt and async noise
            if not line or line == "(gdb)":
                continue
            if line[0] in "*=~&":
                continue
            # Result records
            if line.startswith("^error"):
                raise RuntimeError(f"GDB MI error: {line}")
            for ok in ok_prefixes:
                if line.startswith(ok):
                    return
        
    def mi(self, cmd, verbose=False):
        """
        Sends a GDB command through the GDB process.
    
        Parameters:
            cmd: The GDB command to send.
            verbose: If True, prints the command before sending it. Defaults to False.
        """
        if verbose:
            print(f">>> {cmd}")
        self.gdb_process.stdin.write(cmd + "\n")
        self.gdb_process.stdin.flush()

    def gdb_load_exec(self, elf_image:str="program.elf", timeout=0.3, verbose=False):
        """
        Load and execute an ELF image using GDB.

        Parameters:
            elf_image: Path to the ELF image to be loaded and executed.
            timeout: Timeout for GDB operations.
            verbose: Whether to print verbose output.
        """
        self.gdb_process = subprocess.Popen(
            [self.gdb_exec, '--interpreter=mi2', elf_image],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,  # line-buffered
        )
        self.mi(f"-file-exec-and-symbols {elf_image}", verbose=verbose)
        self.mi_wait_done(timeout=timeout, verbose=verbose)
        self.mi(f"-target-select extended-remote localhost:{self.gdb_port}", verbose=verbose)
        self.mi_wait_done(timeout=timeout, ok_prefixes=("^connected",), verbose=verbose)
        self.mi("-target-download", verbose=verbose)
        self.mi_wait_done(timeout=timeout, ok_prefixes=("^done",), verbose=verbose)
        self.mi("-exec-continue", verbose=verbose)
        self.mi_wait_done(timeout=timeout, ok_prefixes=("^running",), verbose=verbose)

    def gdb_interrupt_disconnect(self, timeout=0.3, halt_target=True, verbose=False):
        """
        Disconnects the GDB target and exits the GDB process.

        Parameters:
            timeout: The maximum time to wait for GDB operations to complete.
            halt_target: Whether to halt the target before disconnecting.
            verbose: Whether to print verbose output.
        """
        if halt_target:
            self.mi("-exec-interrupt", verbose=verbose)
            self.mi_wait_done(timeout=timeout, ok_prefixes=("^done",), verbose=verbose)
            self.mi("-target-disconnect", verbose=verbose)
            self.mi_wait_done(timeout=timeout, ok_prefixes=("^done",), verbose=verbose)
            self.mi("-gdb-exit", verbose=verbose)
            self.mi_wait_done(timeout=timeout, ok_prefixes=("^exit",), verbose=verbose)
        self.gdb_process.terminate()
        self.gdb_process.wait(timeout=timeout)

    def detach(self):
        """
        Detaches from the current debugging session by terminating and closing the necessary processes and socket.
        """
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

    def telnet_init(self):
        """
        Establishes a connection to the OpenOCD telnet server and receives initial messages.
        """
        # generate a connection to the openocd telnet server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)
        self.socket.connect(('localhost', {self.telnet_port}))
        # receive start messages
        time.sleep(0.1)
        self.socket.recv(4096)

    def telnet_interact(self, command:str, wait_time:float = 0.01, verbose:bool = False) -> str:
        """
        Sends a command via Telnet and receives the response.

        Parameters:
            command: The command to send.
            wait_time: Time to wait between sending the command and receiving the response. Defaults to 0.01.
            verbose: Whether to print the response. Defaults to False.

        Returns:
            The response received from the Telnet server.
        """
        if self.openocd_process is None or self.socket is None:
            self.telnet_init()
        command += "\n"
        self.socket.sendall(command.encode("utf-8"))
        time.sleep(wait_time)
        response = self.socket.recv(4096)
        if verbose:
            print(response.decode("utf-8"))
        return response.decode("utf-8")

    def telnet_read_address(self, address:int) -> tuple:
        """
        Reads the memory content at a specified address using Telnet.

        Parameters:
            address: The memory address to read.

        Returns:
            A tuple containing the memory content and the response from the Telnet command.
        """
        command = f"mdw {hex(address)}"
        response = self.telnet_interact(command)
        if "Previous state query failed, trying to reconnect" in response:
            response += self.telnet_interact(command)
        return self.extract_memory_content(response=response, address=address), response

    def telnet_read_image(self, bin_image:str = "memory_dump.bin", start_addr:int = 0x08000000, length:int = 0x400, verbose:bool = False):
        """
        Reads an image from a specified memory address using a telnet connection.
    
        Parameters:
            bin_image: The filename where the dumped image will be saved.
            start_addr: The starting memory address to read from.
            length: The length of the data to read.
            verbose: If True, prints the response from the telnet server.
        """
        command = f"init; dump_image {bin_image} {hex(start_addr)} {hex(length)}; exit"
        response = self.telnet_interact(command)
        if verbose:
            print(response)

    def extract_memory_content(self, response:str, address:int = 0x00) -> int | None:
        """
        Extracts memory content from the response.
        
        Parameters:
            response: The response string to extract memory content from.
            address: The memory address to search for. Defaults to 0x00.
        
        Returns:
            The extracted memory content if found, otherwise None.
        """
        if "Error: Failed to read memory at" not in response:
            match = re.search(fr'{hex(address)[2:]}:\s*([0-9A-Fa-f]+)', response)
            if match:
                return int(match.group(1), 16)
            else:
                return None

    def characterize(self, response:str, mem:int) -> bytes:
        """
        Characterizes the response based on the memory content.
        
        Parameters:
            response: The response string to characterize.
            mem: The memory content to check.

        Returns:
            bytes: A byte string representing the characterization.
        """
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
        """
        Destructor method to detach the debugger when the object is destroyed.
        """
        print("[+] Detaching debugger.")
        self.detach()