# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

from machine import Pin, Timer

class MicroPythonScript():
    def __init__(self):
        self.timer = Timer()
        # LED
        self.led = Pin("LED", Pin.OUT)
        self.led.low()
        # VTARGET_OC (active low, overcurrent response)
        self.pin_vtarget_oc = Pin(21, Pin.OUT, Pin.PULL_UP)
        self.pin_vtarget_oc.high()
        # VTARGET_EN (active low)
        self.pin_power = Pin(20, Pin.OUT, Pin.PULL_UP)
        self.pin_power.high()
        # RESET
        self.pin_reset = Pin(0, Pin.OUT, Pin.PULL_UP)
        self.pin_reset.low()
        # GLITCH_EN
        self.pin_glitch = Pin(1, Pin.OUT, Pin.PULL_DOWN)
        self.pin_glitch.low()
        # TRIGGER
        self.pin_trigger = Pin(15, Pin.IN, Pin.PULL_DOWN)
        # HP_GLITCH
        self.pin_hpglitch = Pin(16, Pin.OUT, Pin.PULL_DOWN)
        self.pin_hpglitch.low()
        # LP_GLITCH
        self.pin_lpglitch = Pin(17, Pin.OUT, Pin.PULL_DOWN)
        self.pin_lpglitch.low()

    def enable_vtarget(self):
        self.pin_power.low()

    def disable_vtarget(self):
        self.pin_power.high()

    def enable_glitch(self):
        self.pin_glitch.low()

    def disable_glitch(self):
        self.pin_glitch.high()

    def enable_hpglitch(self):
        if self.pin_trigger.value():
            self.pin_hpglitch.high()

    def disable_hpglitch(self):
        self.pin_hpglitch.low()

    def enable_lpglitch(self):
        if self.pin_trigger.value():
            self.pin_lpglitch.high()

    def disable_lpglitch(self):
        self.pin_lpglitch.low()

    def reset_target(self):
        self.pin_reset.low()

    def release_reset(self):
        self.pin_reset.high()

    def tick(self):
        self.led.toggle()