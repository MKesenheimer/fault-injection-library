#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.
import time
from findus import PicoGlitcher

glitcher = PicoGlitcher()
glitcher.init(port="/dev/tty.usbmodem1301")
glitcher.rising_edge_trigger()
glitcher.set_multiplexing()

while True:
    mul_config = {"t1": 10_000, "v1": "1.8", "t2": 1_000, "v2": "GND"}
    glitcher.arm_multiplexing(0, mul_config, "VI2")
    glitcher.reset_target(0.01)

    try:
        glitcher.block(timeout=1)
        response = b'Trigger ok'
    except Exception as _:
        response = b'Timeout'

    print(response)
    # wait for one second
    time.sleep(1)