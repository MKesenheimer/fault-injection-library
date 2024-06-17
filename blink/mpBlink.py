# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

from machine import Pin, Timer

class MicroPythonScript():
    def __init__(self):
        self.timer = Timer()
        self.led = Pin("LED", Pin.OUT)

    def tick(self):
        self.led.toggle()

    def blink(self):
        self.timer.init(freq=2.5, mode=Timer.PERIODIC, callback=self.tick)