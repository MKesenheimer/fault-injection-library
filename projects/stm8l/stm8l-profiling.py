#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Adapted for STM8L single-glitch with external trigger + success-pin

import argparse
import logging
import random
import sys
import time

from findus import Database, PicoGlitcher

# Pico GPIO that your bootloader sets HIGH when the “impossible”
# section has been reached
SUCCESS_PIN = 15


class DerivedPicoGlitcher(PicoGlitcher):
    # override init, not __init__, to ensure
    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)

        self.pico_glitcher.pyb.exec_raw_no_follow(
            "import machine\n"
            f"flag_pin = machine.Pin({SUCCESS_PIN}, machine.Pin.IN, machine.Pin.PULL_DOWN)\n"
        )

    def read_success_flag(self) -> bool:
        """Return True if that pin is HIGH (i.e. we hit the 'impossible' section)."""
        out = self.pico_glitcher.pyb.exec_raw_no_follow(f"print(int(flag_pin.value()))\n")
        return bool(int(out.strip()))


class Main:
    def __init__(self, args):
        self.args = args

        logging.basicConfig(
            filename="stm8l_ext_trigger.log",
            filemode="a",
            format="%(asctime)s %(message)s",
            level=logging.INFO,
            force=True,
        )

        # -- initialize glitcher --
        self.glitcher = DerivedPicoGlitcher()
        self.glitcher.init(port=args.rpico)

        # Use external trigger pin (wired from your instrumented bootloader)
        self.glitcher.set_trigger(
            mode="tio",  # edge-trigger mode
            pin_trigger=args.trigger_input,
            edge_type="rising",
        )

        # Single crowbar glitch to GND. If you'd rather do a multiplex-voltage
        # glitch, swap these two lines for:
        #   self.glitcher.set_multiplexing()
        #   self.glitcher.set_mux_voltage(args.vidle)
        self.glitcher.set_lpglitch()

        # -- database for logging --
        self.db = Database(sys.argv, resume=args.resume, nostore=args.no_store)

    def run(self):
        exp_id = 0
        while True:
            # pick random glitch parameters (ns)
            delay = random.randint(*self.args.delay)
            length = random.randint(*self.args.length)

            # arm the Pico: waits for your ext1/2 trigger, then after `delay`
            # fires a single GND-pulse of width `length`
            self.glitcher.arm(delay, length)

            # now reset the STM8L — as soon as it releases reset it will
            # run your patched bootloader, toggle the trigger pin, etc.
            self.glitcher.reset_target(self.args.reset_hold)

            # wait for the PIO state-machine to clear (or timeout)
            try:
                self.glitcher.block(timeout=self.args.block_timeout)
            except Exception:
                success = False
            else:
                # on a clean exit, read your “success” GPIO
                success = self.glitcher.read_success_flag()

            color = "G" if success else "R"
            self.db.insert(exp_id, delay, length, color, b"")  # no serial dump here
            print(f"[{exp_id}] delay={delay}  length={length} → success={success}")
            exp_id += 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="STM8L single-glitch via external trigger + success pin"
    )
    p.add_argument("--rpico", default="/dev/ttyUSB1", help="PicoGlitcher serial port")
    p.add_argument(
        "--trigger-input",
        default="ext1",
        choices=["default", "alt", "ext1", "ext2"],
        help="Which Pico GPIO to use as trigger",
    )
    p.add_argument(
        "--delay", nargs=2, type=int, required=True, help="Glitch offset range (ns)"
    )
    p.add_argument(
        "--length",
        nargs=2,
        type=int,
        required=True,
        help="Glitch pulse width range (ns)",
    )
    p.add_argument(
        "--reset-hold", type=float, default=0.01, help="Target reset hold time (s)"
    )
    p.add_argument(
        "--block-timeout",
        type=float,
        default=1.0,
        help="Timeout waiting for glitch (s)",
    )
    p.add_argument("--resume", action="store_true", help="Resume previous database run")
    p.add_argument(
        "--no-store", action="store_true", help="Do not write results to the database"
    )
    args = p.parse_args()

    try:
        Main(args).run()
    except KeyboardInterrupt:
        print("Interrupted, exiting.")
        sys.exit(1)
