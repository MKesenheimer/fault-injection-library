#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Adapted for STM8L single-glitch with external trigger + success-pin

import argparse
import logging
import random
import sys
import time

from findus import AnalogPlot, Database, PicoGlitcher

# Pico GPIO that your bootloader sets HIGH when the “impossible”
# section has been reached
SUCCESS_PIN = 20
EXPECTED_PIN = 21


class DerivedPicoGlitcher(PicoGlitcher):
    # override init, not __init__, to ensure
    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)

        self.pico_glitcher.pyb.exec_raw_no_follow(
            "import machine\n"
            f"flag_pin = machine.Pin({SUCCESS_PIN}, machine.Pin.IN, machine.Pin.PULL_DOWN)\n"
        )
        self.pico_glitcher.pyb.exec_raw_no_follow(
            f"expected_pin = machine.Pin({EXPECTED_PIN}, machine.Pin.IN, machine.Pin.PULL_DOWN)\n"
        )

    def read_success_flag(self) -> bool:
        """Return True if that pin is HIGH (i.e. we hit the 'impossible' section)."""
        out = self.pico_glitcher.pyb.exec_raw(f"print(int(flag_pin.value()))\n")
        return bool(int(out[0].strip()))

    def read_expected_flag(self) -> bool:
        """Return True if the expected pin is HIGH."""
        out = self.pico_glitcher.pyb.exec_raw(f"print(int(expected_pin.value()))\n")
        return bool(int(out[0].strip()))


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
        self.glitcher.change_config_and_reset("mux_vinit", "3.3")
        self.glitcher.init(port=args.rpico)

        # Use external trigger pin (wired from your instrumented bootloader)
        self.glitcher.rising_edge_trigger()

        self.glitcher.set_multiplexing()
        # self.glitcher.set_lpglitch()

        # -- database for logging --
        self.db = Database(sys.argv, resume=args.resume, nostore=args.no_store)
        self.start_time = int(time.time())

        self.number_of_samples = 1024
        self.sampling_freq = 450_000
        self.glitcher.configure_adc(
            number_of_samples=self.number_of_samples,
            sampling_freq=self.sampling_freq,
        )
        self.plotter = AnalogPlot(
            number_of_samples=self.number_of_samples,
            sampling_freq=self.sampling_freq,
        )

    def run(self):
        s_length = self.args.length[0]
        e_length = self.args.length[1]
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]

        exp_id = 0
        while True:
            # pick random glitch parameters (ns)
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            mul_config = {"t1": length, "v1": "GND"}
            self.glitcher.arm_multiplexing(delay, mul_config)
            # self.glitcher.arm(delay, length)
            self.glitcher.arm_adc()

            # time.sleep(0.01)
            # now reset the STM8L — as soon as it releases reset it will
            # run your patched bootloader, toggle the trigger pin, etc.
            self.glitcher.reset_target(0.001)
            # TODO: send uart command to the target to start

            status = b"unknown"

            # wait for the PIO state-machine to clear (or timeout)
            try:
                self.glitcher.block(timeout=2)

                # on a clean exit, read your “success” GPIO
                success = self.glitcher.read_success_flag()
                expected = self.glitcher.read_expected_flag()

                if not (success or expected):
                    time.sleep(0.01)  # wait a bit for the GPIO to settle
                    success = self.glitcher.read_success_flag()
                    expected = self.glitcher.read_expected_flag()

                print(f"[{exp_id}] success={success} expected={expected}")

                if success:
                    status = b"success"
                    # break
                elif expected:
                    status = b"expected"
                else:
                    status = b"error"

                samples = self.glitcher.get_adc_samples()
                self.plotter.update_curve(samples)
            except Exception as e:
                status = b"timeout"
                self.glitcher.power_cycle_target(power_cycle_time=1)
                print(f"[{exp_id}] Error: {e}")

            color = self.glitcher.classify(status)
            self.db.insert(exp_id, delay, length, color, status)  # no serial dump here
            print(
                f"[{exp_id}] delay={delay}  length={length} → status={status} ({color})"
            )
            exp_id += 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="STM8L single-glitch via external trigger + success pin"
    )
    p.add_argument("--rpico", default="/dev/ttyUSB1", help="PicoGlitcher serial port")
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
    p.add_argument(
        "--trigger-input",
        default="default",
        help="The trigger input to use (default, alt, ext1, ext2). The inputs ext1 and ext2 require the PicoGlitcher v2.",
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
