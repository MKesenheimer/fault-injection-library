#!/usr/bin/env python3

import argparse
import logging
import random
import sys
import time

# import custom libraries
from findus import Database, PicoGlitcher, STM8Programmer

class DerivedPicoGlitcher(PicoGlitcher):
    def classify(self, state: bytes) -> str:
        color = 'C'
        # do i need this line?
        if b'error: sending read memory command failed' == state:
            color = 'G'
        elif b'error' in state:
            color = 'M'
        elif b'warning' in state:
            color = 'O'
        elif b'timeout' in state:
            color = 'Y'
        elif b'ok' in state:
            color = 'C'
        elif b'success' in state:
            color = 'R'
        return color

class Main:
    def __init__(self, args):
        self.args = args

        logging.basicConfig(
            filename="stm8l_double_glitch.log",
            filemode="a",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            force=True
        )

        # Initialize glitcher and programmer
        self.glitcher = DerivedPicoGlitcher()
        self.glitcher.init(port=args.rpico)
        self.glitcher.change_config_and_reset("mux_vinit", args.vinit)
        self.glitcher.init(port=args.rpico)

        # Always use multiplexing for double glitch
        self.glitcher.set_multiplexing()
        # Ensure we start from the normal operating voltage
        self.glitcher.set_mux_voltage("3.3")

        self.programmer = STM8Programmer(port=args.target, baud=115200)
        self.database = Database(sys.argv, resume=args.resume, nostore=args.no_store)
        self.start_time = time.time()

    def run(self):
        logging.info("Starting STM8L double-multiplex glitch campaign")
        exp_id = 0

        while True:
            # Randomly pick glitch parameters within given bounds
            t0 = random.randint(*self.args.delay0)
            w0 = random.randint(*self.args.width0)
            t1 = random.randint(*self.args.delay1)
            w1 = random.randint(*self.args.width1)

            # Arm the double-multiplex glitch:
            #   T0, W0 are offset/width of first glitch,
            #   T1, W1 of second, relative to end of first
            self.glitcher.arm_double_multiplexing(
                t0, w0, t1, w1,
                v1=self.args.v1, v2=self.args.v2
            )

            # Trigger the glitch by resetting the target
            self.glitcher.reset_target(self.args.reset_hold)
            time.sleep(self.args.post_reset_delay)

            # TODO instead just check if pin 2 (USART_RX) is high
            state = self.programmer.bootloader_enter()
            flash = b''
            eeprom = b''
            
            if b'success' in state:
                # Attempt to read firmware dump
                state, flash = self.programmer.read_memory(address=0x8000, length=0x2000)
                _, eeprom = self.programmer.read_memory(address=0x1000, length=0xFF)

            # Block until both glitches have fired (or timeout)
            try:
                self.glitcher.block(timeout=self.args.block_timeout)
            except Exception:
                state = b'timeout'
                logging.warning(f"Experiment {exp_id}: timeout")

            color = self.glitcher.classify(state)
            self.database.insert(exp_id, t0, w0, t1, w1, color, state + flash + eeprom)

            print(f"[{exp_id}] T0={t0} W0={w0}  T1={t1} W1={w1} → {state.decode()}", flush=True)
            exp_id += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="STM8L double-multiplexing glitch campaign"
    )
    parser.add_argument("--target", default="/dev/ttyUSB0",
                        help="STM8L target serial port")
    parser.add_argument("--rpico", default="/dev/ttyUSB1",
                        help="PicoGlitcher serial port")
    parser.add_argument("--delay0", required=True, nargs=2, type=int,
                        help="First glitch offset range (µs)")
    parser.add_argument("--width0", required=True, nargs=2, type=int,
                        help="First glitch width range (ns)")
    parser.add_argument("--delay1", required=True, nargs=2, type=int,
                        help="Second glitch offset range (µs) relative to end of first")
    parser.add_argument("--width1", required=True, nargs=2, type=int,
                        help="Second glitch width range (ns)")
    parser.add_argument("--v1", default="1.8",
                        help="Voltage for both glitch pulses (e.g. '1.8')")
    parser.add_argument("--v2", default="1.8",
                        help="Voltage after second glitch (e.g. '3.3' or same as v1)")
    parser.add_argument("--vinit", default="3.3",
                        help="Initial VCC level before any glitch")
    parser.add_argument("--reset-hold", type=float, default=0.01,
                        help="Reset line hold time (s)")
    parser.add_argument("--post-reset-delay", type=float, default=0.01,
                        help="Time to wait after reset before block()")
    parser.add_argument("--block-timeout", type=float, default=1.0,
                        help="Timeout for blocking on PIO IRQ (s)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume previous database run")
    parser.add_argument("--no-store", action="store_true",
                        help="Do not store results in database")
    args = parser.parse_args()

    main = Main(args)
    try:
        main.run()
    except KeyboardInterrupt:
        print("Interrupted by user, exiting.")    
