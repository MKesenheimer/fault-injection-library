#!/usr/bin/env python3

import argparse
import logging
import os
import random
import sys
import time
import requests

import numpy as np

from findus import Database, PicoGlitcher, Serial


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
    if response.status_code == 200:
        print("Notification sent successfully!")
    else:
        print(f"Failed to send notification: {response.text}")


class DerivedPicoGlitcher(PicoGlitcher):
    def classify(self, state: bytes) -> str:
        color = "C"
        if b"error" in state:
            color = "M"
        elif b"expected" in state:
            color = "G"
        elif b"timeout" in state:
            color = "Y"
        elif b"reset" in state:
            color = "O"
        elif b"success" in state:
            color = "R"
        return color


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

        self.glitcher = DerivedPicoGlitcher()
        self.glitcher.init(port=args.rpico, enable_vtarget=False)
        self.glitcher.change_config_and_reset("mux_vinit", "3.3")
        self.glitcher.init(port=args.rpico, enable_vtarget=False)

        self.glitcher.rising_edge_trigger()

        self.glitcher.set_multiplexing()
        self.glitcher.power_cycle_reset(0.01)

        self.db = Database(sys.argv, resume=args.resume, nostore=args.no_store)
        self.start_time = int(time.time())

        self.target = Serial(port=args.target, baudrate=9600)

    def run(self):
        s_length = self.args.length[0]
        e_length = self.args.length[1]
        """ 
        Measured with logic analyzer:
        - Length of trigger pulse (loop logic): ~36 ms
        """
        s_delay = self.args.delay[0]
        e_delay = self.args.delay[1]

        exp_id = 0

        while True:
            # for delay in np.arange(s_delay, e_delay + 1, 5):
            #     for length in np.arange(s_length, e_length + 1, 5):
            #         for _ in range(100):
            # delay = int(delay)
            # length = int(length)
            delay = random.randint(s_delay, e_delay)
            length = random.randint(s_length, e_length)

            mul_config = {"t1": length, "v1": "VI1"}
            self.glitcher.arm_multiplexing(delay, mul_config)

            # trigger the loop and glitch
            self.target.write(b"g")

            try:
                self.glitcher.block(timeout=2)

                response_cmd = self.target.read(1)

                if response_cmd == b"":
                    state = b"error"
                elif response_cmd != b"r":
                    state = b"error: unexpected response cmd: " + response_cmd
                else:
                    raw_payload = self.target.readline()

                    if len(raw_payload) != 9:
                        state = b"error: unexpected payload length: " + raw_payload
                    else:
                        cnt = int(raw_payload, 16)

                        if cnt == 2500:
                            state = b"expected"
                        else:
                            print(
                                f"[-] Unexpected response: {raw_payload}, cnt = {cnt}"
                            )
                            state = b"success"

            except Exception:
                print("[-] Timeout received in block(). Continuing.")
                self.glitcher.power_cycle_reset(0.2)
                time.sleep(0.2)
                state = b"timeout"

            try:
                self.target.write(b"r")
                response = self.target.readline()
                rst = int(response[1:])
                if rst != 0 and state != b"timeout":
                    state = b"reset"
            except:
                state = b"error: no reset"
                print(response)

            color = self.glitcher.classify(state)
            self.db.insert(exp_id, delay, length, color, state)
            speed = self.glitcher.get_speed(self.start_time, exp_id)
            experiment_base_id = self.db.get_base_experiments_count()
            print(
                self.glitcher.colorize(
                    f"[+] Experiment {exp_id}\t{experiment_base_id}\t({speed})\t{delay:>{len(str(e_delay))}}\t{length}\t{color}\t{state}",
                    color,
                )
            )
            self.target.flush()
            exp_id += 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="STM8L single-glitch via external trigger + success pin"
    )
    p.add_argument("--rpico", default="/dev/ttyUSB1", help="PicoGlitcher serial port")
    p.add_argument("--target", default="/dev/ttyUSB2", help="Target serial port")
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
