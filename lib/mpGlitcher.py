# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import machine
from rp2 import asm_pio, PIO, StateMachine
from machine import Pin
import time

# number of bits for UART
BITS = 8

@asm_pio(set_init=(PIO.OUT_LOW))
def glitch_tio_trigger():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until length received
    pull(block)
    mov(y, osr)

    # wait for rising on trigger pin
    wait(0, gpio, 15)
    wait(1, gpio, 15)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # emit glitch
    set(pins, 0b1)
    label("length_loop")       
    jmp(y_dec, "length_loop")
    set(pins, 0b0)

    # tell execution finished
    push(block)

@asm_pio(set_init=(PIO.OUT_LOW))
def glitch_uart_trigger():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until length received
    pull(block)
    mov(y, osr)

    # wait for irq in uart_trigger state machine
    wait(1, irq, 7)

    # wait delay
    label("delay_loop")       
    jmp(x_dec, "delay_loop")

    # emit glitch
    set(pins, 0b1)
    label("length_loop")       
    jmp(y_dec, "length_loop")
    set(pins, 0b0)

    # tell execution finished
    push(block)

@asm_pio(in_shiftdir = PIO.SHIFT_RIGHT)
def uart_trigger(BITS=BITS):
    # block until pattern received
    pull(block)
    mov(x, osr)

    label("start")
    mov(isr, null)
    # Wait for start bit
    wait(0, pin, 0)
    # Preload bit counter, delay until eye of first data bit
    set(y, BITS - 1) [10]
    # Loop 9 times
    label("bitloop")
    # Sample data, shift sampled data into ISR
    in_(pins, 1)
    # Each iteration is 8 cycles
    jmp(y_dec, "bitloop") [6]

    # compare received data with supplied pattern
    mov(y, isr)
    jmp(x_not_y, "start")

    # if received data matches pattern, set the irq and activate the glitch
    irq(block, 7)

    # wrap around
    jmp("start")

class MicroPythonScript():
    def __init__(self):
        self.sm1 = None
        self.sm2 = None
        self.frequency = None
        self.trigger = None
        self.baudrate = 115200
        self.set_frequency(200_000_000)
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
        self.pin_glitch_en = Pin(1, Pin.OUT, Pin.PULL_DOWN)
        self.pin_glitch_en.low()
        # TRIGGER
        self.pin_trigger = Pin(15, Pin.IN, Pin.PULL_DOWN)
        # HP_GLITCH
        self.pin_hpglitch = Pin(16, Pin.OUT, Pin.PULL_DOWN)
        self.pin_hpglitch.low()
        # LP_GLITCH
        self.pin_lpglitch = Pin(17, Pin.OUT, Pin.PULL_DOWN)
        self.pin_lpglitch.low()

    def set_frequency(self, frequency=200_000_000):
        machine.freq(frequency)
        self.frequency = machine.freq()

    def set_trigger(self, trigger="tio"):
        self.trigger = trigger

    def set_baudrate(self, baud=115200):
        self.baudrate = baud

    def set_pattern_match(self, pattern):
        self.pattern = pattern

    def enable_vtarget(self):
        self.pin_power.low()

    def disable_vtarget(self):
        self.pin_power.high()

    def power_cycle_target(self, power_cycle_time=0.2):
        self.disable_vtarget()
        time.sleep(power_cycle_time)
        self.enable_vtarget()
        self.pin_glitch_en.low()

    def reset_low(self):
        self.pin_reset.low()

    def reset_high(self):
        self.pin_reset.high()

    def reset_target(self):
        self.pin_reset.low()

    def release_reset(self):
        self.pin_reset.high()

    def reset(self, reset_time=0.01):
        self.reset_target()
        time.sleep(reset_time)
        self.release_reset()
        self.pin_glitch_en.low()

    def arm(self, delay, length):
        self.release_reset()
        self.pin_glitch_en.high()
        self.enable_vtarget()
        self.pin_hpglitch.low()
        self.pin_lpglitch.low()

        if self.trigger == "tio":
            # TODO: je nachdem ob hp oder lp glitch: set_base setzen
            self.sm1 = StateMachine(1, glitch_tio_trigger, freq=self.frequency, set_base=self.pin_hpglitch)
            self.sm1.active(1)
            # push delay and length into the fifo of the statemachine
            self.sm1.put(delay // (1_000_000_000 // self.frequency))
            self.sm1.put(length // (1_000_000_000 // self.frequency))
        
        elif self.trigger == "uart":
            # TODO: je nachdem ob hp oder lp glitch: set_base setzen
            self.sm1 = StateMachine(1, glitch_uart_trigger, freq=self.frequency, set_base=self.pin_hpglitch)
            self.sm1.active(1)
            # push delay and length into the fifo of the statemachine
            self.sm1.put(delay // (1_000_000_000 // self.frequency))
            self.sm1.put(length // (1_000_000_000 // self.frequency))

            self.sm2 = StateMachine(2, uart_trigger, freq=self.baudrate * 8, in_base=self.pin_trigger)
            self.sm2.active(1)
            # push pattern into the fifo of the statemachine
            pattern = self.pattern << (32 - BITS)
            self.sm2.put(pattern)

    def deactivate_sm1(self):
        self.sm1.active(0)

    def restart_sm1(self):
        self.sm1.restart()

    def block(self):
        if self.sm1 is not None:
            # wait until statemachine execution is finished
            self.sm1.get()

    def get_sm2_output(self):
        if self.sm2 is not None:
            # pull the output of statemachine 2
            res = self.sm2.get()
            print(res)