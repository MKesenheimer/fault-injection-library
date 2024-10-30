# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

"""
This is the documentation of the mpGlitcher module and all its classes.

Upload this module onto your PicoGlitcher. The classes and methods will become available through the pyboard interface.
"""

import machine
from rp2 import asm_pio, PIO, StateMachine
from machine import Pin
import time

@asm_pio(set_init=(PIO.OUT_LOW), in_shiftdir=PIO.SHIFT_RIGHT)
def glitch_tio_trigger():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until length received
    pull(block)
    mov(y, osr)

    # wait for irq in block_condition state machine
    wait(1, irq, 7)

    # wait for rising edge on trigger pin
    #wait(0, gpio, 18) # Trigger 1 (without level shifter)
    #wait(1, gpio, 18)
    wait(0, gpio, 15) # Trigger 2 (with level shifter)
    wait(1, gpio, 15)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # emit glitch at base pin
    set(pins, 0b1)
    label("length_loop")       
    jmp(y_dec, "length_loop")
    set(pins, 0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def block_condition():
    # block until dead time received
    pull(block)
    mov(x, osr)
    # block until condition is received (wait for 0 or 1)
    pull(block)
    mov(y, osr)

    # wait for condition
    wait(y, pin, 0)

    # wait dead time
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # tell execution finished (fills the sm's fifo buffer)
    irq(block, 7)

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

    # emit glitch at base pin
    set(pins, 0b1)
    label("length_loop")       
    jmp(y_dec, "length_loop")
    set(pins, 0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def uart_trigger():
    # block until pattern received
    pull(block)
    mov(x, osr)
    # block until number of bits (self.number_of_bits - 1) received
    pull(block)
    mov(y, osr)

    label("start")
    mov(isr, null)
    # Wait for start bit
    wait(0, pin, 0)
    # delay until eye of first data bit
    nop() [10]
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
    """
    MicroPython class that contains the code to access the hardware of the PicoGlitcher.

    Methods:
        __init__: Default constructor.
        set_frequency: 
        set_trigger: 
        set_baudrate:
        set_pattern_match:
        enable_vtarget:
        power_cycle_target:
        reset_target:
        release_reset:
        reset:
        set_lpglitch:
        set_hpglitch:
        set_dead_zone:
        arm:
        block:
        get_sm2_output:
    """
    def __init__(self):
        self.sm1 = None
        self.sm2 = None
        self.frequency = None
        self.trigger = None
        self.baudrate = 115200
        self.number_of_bits = 8
        self.set_frequency(200_000_000) # overclocking supposedly works, script runs also with 270_000_000
        # LED
        self.led = Pin("LED", Pin.OUT)
        self.led.low()
        # VTARGET_OC (active low, overcurrent response)
        self.pin_vtarget_oc = Pin(21, Pin.IN, Pin.PULL_UP)
        # VTARGET_EN (active low)
        self.pin_vtarget_en = Pin(20, Pin.OUT, Pin.PULL_UP)
        self.pin_vtarget_en.high()
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
        # which glitching transistor to use. Default: lpglitch
        self.pin_glitch = self.pin_lpglitch
        # standard dead zone after power down
        self.dead_time = 0.05
        self.pin_condition = self.pin_vtarget_en
        self.condition = 0

    def set_frequency(self, frequency=200_000_000):
        machine.freq(frequency)
        self.frequency = machine.freq()

    def set_trigger(self, trigger="tio"):
        self.trigger = trigger

    def set_baudrate(self, baud=115200):
        self.baudrate = baud

    def set_number_of_bits(self, number_of_bits:int = 8):
        self.number_of_bits = number_of_bits

    def set_pattern_match(self, pattern):
        self.pattern = pattern

    def enable_vtarget(self):
        self.pin_vtarget_en.low()

    def disable_vtarget(self):
        self.pin_vtarget_en.high()

    def power_cycle_target(self, power_cycle_time=0.2):
        self.disable_vtarget()
        time.sleep(power_cycle_time)
        self.enable_vtarget()
        self.pin_glitch_en.low()

    def reset_target(self):
        self.pin_reset.low()

    def release_reset(self):
        self.pin_reset.high()

    def reset(self, reset_time=0.01):
        self.reset_target()
        time.sleep(reset_time)
        self.release_reset()
        self.pin_glitch_en.low()

    def set_lpglitch(self):
        self.pin_glitch = self.pin_lpglitch

    def set_hpglitch(self):
        self.pin_glitch = self.pin_hpglitch

    def set_dead_zone(self, dead_time=0.05, pin="power"):
        if pin == "power":
            self.pin_condition = self.pin_vtarget_en
            # wait until VTARGET_EN is high (meaning VTARGET is disabled)
            self.condition = 1
        elif pin == "reset":
            self.pin_condition = self.pin_reset
            # wait until RESET is low
            self.condition = 0
        self.dead_time = dead_time

    def arm(self, delay, length):
        self.release_reset()
        self.pin_glitch_en.high()
        self.pin_hpglitch.low()
        self.pin_lpglitch.low()

        if self.trigger == "tio":
            # state machine that emits the glitch if the trigger condition is met
            self.sm1 = StateMachine(1, glitch_tio_trigger, freq=self.frequency, set_base=self.pin_glitch)
            self.sm1.active(1)
            # push delay and length (in nano seconds) into the fifo of the statemachine
            self.sm1.put(delay // (1_000_000_000 // self.frequency))
            self.sm1.put(length // (1_000_000_000 // self.frequency))

            # state machine that blocks for a specific time after a certain condition (dead time)
            self.sm2 = StateMachine(2, block_condition, freq=self.frequency, in_base=self.pin_condition)
            self.sm2.active(1)
            # push dead time (in seconds) into the fifo of the statemachine and decide what condition must be met (0 or 1)
            self.sm2.put(int(self.dead_time * self.frequency))
            self.sm2.put(self.condition)
        
        elif self.trigger == "uart":
            # state machine that emits the glitch if the trigger condition is met
            self.sm1 = StateMachine(1, glitch_uart_trigger, freq=self.frequency, set_base=self.pin_glitch)
            self.sm1.active(1)
            # push delay and length (in nano seconds) into the fifo of the statemachine
            self.sm1.put(delay // (1_000_000_000 // self.frequency))
            self.sm1.put(length // (1_000_000_000 // self.frequency))

            # state machine that checks the trigger condition
            self.sm2 = StateMachine(2, uart_trigger, freq=self.baudrate * 8, in_base=self.pin_trigger)
            self.sm2.active(1)
            # push pattern into the fifo of the statemachine
            pattern = self.pattern << (32 - self.number_of_bits)
            self.sm2.put(pattern)
            # push number of bits into the fifo of the statemachine (self.number_of_bits - 1 is an optimization here)
            self.sm2.put(self.number_of_bits - 1)

    def block(self, timeout):
        if self.sm1 is not None:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.sm1.rx_fifo() > 0:
                    break
            if time.time() - start_time >= timeout:
                raise Exception("Function execution timed out!")

    def get_sm2_output(self):
        if self.sm2 is not None:
            # pull the output of statemachine 2
            res = self.sm2.get()
            print(res)