#!/usr/bin/env python3

import argparse
import logging
import os
import sys
import time
import numpy as np
from serial import Serial
import requests
from dotenv import load_dotenv

from findus import Database, PicoGlitcher

SUCCESS_PIN = 20
RESET_PIN = 21


def send_pushover_notification(user_key, app_token, message, title=None):
    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": app_token,
        "user": user_key,
        "message": message,
    }
    if title:
        payload["title"] = title

    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Failed to send notification: {response.text}")


class DerivedPicoGlitcher(PicoGlitcher):
    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)

        self.pico_glitcher.pyb.exec_raw_no_follow(
            "import machine\n"
            f"success_pin = machine.Pin({SUCCESS_PIN}, machine.Pin.IN, machine.Pin.PULL_DOWN)\n"
            f"reset_pin = machine.Pin({RESET_PIN}, machine.Pin.IN, machine.Pin.PULL_DOWN)\n"
        )

    def read_success_flag(self) -> bool:
        out = self.pico_glitcher.pyb.exec_raw(f"print(int(success_pin.value()))\n")
        return bool(int(out[0].strip()))

    def read_reset_flag(self) -> bool:
        out = self.pico_glitcher.pyb.exec_raw(f"print(int(reset_pin.value()))\n")
        return bool(int(out[0].strip()))

    def classify(self, state: bytes) -> str:
        color = "C"
        if b"expected" in state:
            color = "G"
        elif b"ok" in state:
            color = "C"
        elif b"error" in state:
            color = "M"
        elif b"timeout" in state:
            color = "Y"
        elif b"warning" in state:
            color = "O"
        elif b"success" in state:
            color = "R"
        return color


class PS3005D:
    def __init__(self, port):
        self.device = Serial(port=port, baudrate=9600)

    def get_voltage(self) -> float:
        """
        Gets the current output voltage of the psu

        Returns:
            float: The current output voltage, in volts (V).
        """
        self.device.write("VSET1?".encode())
        response = self.device.read(5).decode().strip()

        return float(response)

    def set_voltage(self, voltage: float, attempts: int = 10):
        """
        Sets the output voltage of the psu

        Args:
            voltage (float): The voltage to set, in volts (V).
        """
        self.device.write(f"VSET1:{voltage:05.2f}".encode())

    def set_current_limit(self, current: float):
        """
        Sets the current limit of the psu

        Args:
            current (float): The current limit to set, in amperes (A).
        """
        self.device.write(f"ISET1:{current:.3f}".encode())

    def turn_on(self):
        self.device.write("OUT1".encode())

    def turn_off(self):
        self.device.write("OUT0".encode())


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
        self.glitcher.init(port=args.rpico, enable_vtarget=False)
        self.glitcher.change_config_and_reset("mux_vinit", "3.3")
        self.glitcher.init(port=args.rpico, enable_vtarget=False)

        self.glitcher.rising_edge_trigger()
        self.glitcher.set_multiplexing()

        self.glitcher.power_cycle_reset(0.01)

        self.db = Database(sys.argv, resume=args.resume, nostore=args.no_store, column_names=["voltage", "delay", "length"])
        self.start_time = int(time.time())

        self.psu = PS3005D(port=args.psu)

    def run(self):
        s_length = 0
        e_length = 150
        length_step = 5
        s_delay = 0
        e_delay = 1000
        delay_step = 6
        s_voltage = 1.70
        e_voltage = 1.96
        voltage_step = 0.01
        n_glitches = 200

        expected_glitches_per_second = 34
        total_glitches = (
            (e_voltage - s_voltage)
            / voltage_step
            * (e_delay - s_delay)
            / delay_step
            * (e_length - s_length)
            / length_step
            * n_glitches
        )
        total_experiment_length = total_glitches / expected_glitches_per_second
        print(
            f"Total glitches: {total_glitches}, expected experiment length: {total_experiment_length:.2f} seconds"
        )

        exp_id = 0

        self.psu.set_voltage(s_voltage)
        time.sleep(0.1)
        self.psu.set_current_limit(0.5)
        time.sleep(0.1)
        self.psu.turn_on()
        time.sleep(0.1)

        # while True:
        for voltage in np.arange(s_voltage, e_voltage + 0.01, 0.01):
            print(f"Setting PSU voltage to {voltage:.2f} V")
            self.psu.set_voltage(voltage)
            time.sleep(0.1)
            
            for delay in np.arange(s_delay, e_delay, delay_step):
                for length in np.arange(s_length, e_length, length_step):
                    for _ in range(n_glitches):
                        delay = int(delay)
                        length = int(length)

                        mul_config = {"t1": length, "v1": "VI1"}
                        self.glitcher.arm_multiplexing(delay, mul_config)

                        self.glitcher.reset(0.001)

                        try:
                            self.glitcher.block(timeout=1)
                            time.sleep(0.001)

                            success = self.glitcher.read_success_flag()
                            reset = self.glitcher.read_reset_flag()
                            print(f"success={success}, reset={reset}")

                            if success:
                                state = b"success"
                                send_pushover_notification(
                                    user_key=os.getenv("PUSHOVER_USER_KEY"),
                                    app_token=os.getenv("PUSHOVER_APP_TOKEN"),
                                    message=f"Successful glitch! with delay={delay} ns, length={length} ns, voltage={voltage:.2f} V",
                                    title="Successful glitch",
                                )
                            elif reset:
                                state = b"reset"
                            else:
                                state = b"expected"
                        except:
                            print("[-] Timeout received in block(). Continuing.")
                            self.glitcher.power_cycle_reset(0.2)
                            time.sleep(0.2)
                            state = b"timeout"

                        color = self.glitcher.classify(state)
                        self.db.insert(exp_id, voltage * 100, delay, length, color, state)
                        speed = self.glitcher.get_speed(self.start_time, exp_id)
                        experiment_base_id = self.db.get_base_experiments_count()
                        print(
                            self.glitcher.colorize(
                                f"[+] Experiment {exp_id}\t{experiment_base_id}\t({speed})\t{voltage:.2f}\t{delay:>{len(str(e_delay))}}\t{length}\t{color}\t{state}",
                                color,
                            )
                        )
                        exp_id += 1

        self.psu.turn_off()


if __name__ == "__main__":
    load_dotenv()

    p = argparse.ArgumentParser(
        description="STM8L single-glitch via external trigger + success pin"
    )
    p.add_argument(
        "--rpico",
        default="/dev/ttyUSB1",
        required=True,
        help="PicoGlitcher serial port",
    )
    p.add_argument(
        "--psu", default="/dev/ttyUSB0", required=True, help="PSU serial port"
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
