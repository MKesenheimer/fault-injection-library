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
from mpConfig import *

if hardware_version[0] == 1:
    # Trigger 1 (without level shifter)
    ALT_TRIGGER = 18
    # Trigger 2 (with level shifter)
    TRIGGER = 15
    VTARGET_OC = 21
    VTARGET_EN = 20
    RESET = 0
    GLITCH_EN = 1
    HP_GLITCH = 16
    LP_GLITCH = 17
elif hardware_version[0] == 2:
    TRIGGER = 14
    # alternative trigger on EXT1
    ALT_TRIGGER = 11
    VTARGET_EN = 22
    RESET = 2
    GLITCH_EN = 3
    HP_GLITCH = 12
    HP_GLITCH_LED = 8
    LP_GLITCH = 13
    LP_GLITCH_LED = 7
    MUX0 = 1
    MUX1 = 0
    EXT1 = 11
    EXT2 = 10

@asm_pio(set_init=(PIO.OUT_LOW), sideset_init=(PIO.OUT_LOW), in_shiftdir=PIO.SHIFT_RIGHT)
def glitch():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until length received
    pull(block)
    mov(y, osr)

    # enable pin_glitch_en
    nop().side(0b1)

    # wait for trigger condition
    wait(1, irq, 7)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # emit glitch at base pin
    set(pins, 0b1)
    label("length_loop")       
    jmp(y_dec, "length_loop")
    set(pins, 0b0)

    # disable pin_glitch_en
    nop().side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(set_init=(PIO.OUT_LOW, PIO.OUT_LOW), sideset_init=(PIO.OUT_LOW), in_shiftdir=PIO.SHIFT_RIGHT)
def pulse():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until length received
    pull(block)
    mov(y, osr)

    # enable pin_glitch_en
    nop().side(0b1)

    # wait for trigger condition
    wait(1, irq, 7)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # emit glitch at base pin
    # lsb: GPIO0 -> MUX1
    # msb: GPIO1 -> MUX0
    # 0b00: IN1 = 1: VCC
    # 0b01: IN3 = 1: +1V8
    # 0b10: IN2 = 1: +3V3
    # 0b11: IN4 = 1: GND
    set(pins, 0b01)
    label("length_loop")       
    jmp(y_dec, "length_loop")
    set(pins, 0b11)

    mov(y, osr)
    label("length_loop2")       
    jmp(y_dec, "length_loop2")
    set(pins, 0b00)

    # disable pin_glitch_en
    nop().side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def tio_trigger():
    label("start")

    # wait for irq in block_rising_condition or block_falling_condition state machine (dead time)
    wait(1, irq, 6)

    # wait for rising edge on trigger pin
    wait(0, pin, 0)
    wait(1, pin, 0)

    # tell observed trigger
    irq(block, 7)

    # wrap around
    jmp("start")

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def block_rising_condition():
    # block until dead time received
    pull(block)
    mov(x, osr)

    # wait for rising edge condition
    wait(1, pin, 0)

    # wait dead time
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # tell execution finished (fills the sm's fifo buffer)
    irq(block, 6)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def block_falling_condition():
    # block until dead time received
    pull(block)
    mov(x, osr)

    # wait for falling edge condition
    wait(0, pin, 0)

    # wait dead time
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # tell execution finished (fills the sm's fifo buffer)
    irq(block, 6)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def test():
    # block until dead time received
    pull(block)
    mov(x, osr)

    # get the content of x with function get_sm2_output()
    mov(isr, x)
    push(block)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def uart_trigger():
    # block until pattern received
    pull(block)
    mov(x, osr)
    # block until number of bits (self.number_of_bits - 1) received, store in osr
    pull(block)

    label("start")
    mov(isr, null)
    # Wait for start bit
    wait(0, pin, 0)
    # Preload bit counter, delay until eye of first data bit
    mov(y, osr) [10]
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
        __init__: Default constructor. Initializes the PicoGlitcher with the default configuration.
        get_firmware_version: Get the current firmware version. Can be used to check if the current version is compatible with findus.
        set_frequency: Set the CPU frequency of the Raspberry Pi Pico.
        get_frequency: Get the current CPU frequency of the Raspberry Pi Pico.
        set_trigger: Configures the PicoGlitcher which triggger condition to use.
        set_baudrate: Set the baudrate of the UART communication in UART-trigger mode.
        set_number_of_bits: Set the number of bits of the UART communication in UART-trigger mode.
        set_pattern_match: Configure the PicoGlitcher to trigger when a specific byte pattern is observed on the RX line (`TRIGGER` pin).
        enable_vtarget: Enable `VTARGET` output. Activates the PicoGlitcher's power supply for the target.
        disable_vtarget: Disables `VTARGET` output. Disables the PicoGlitcher's power supply for the target.
        power_cycle_target: Power cycle the target via the PicoGlitcher `VTARGET` output.
        reset_target: Reset the target via the PicoGlitcher's `RESET` output.
        release_reset: Release the reset on the target via the PicoGlitcher's `RESET` output.
        reset: Reset the target via the PicoGlitcher's `RESET` output, release the reset on the target after a certain time.
        set_lpglitch: Enable the low-power crowbar MOSFET for glitch generation.
        set_hpglitch: Enable the high-power crowbar MOSFET for glitch generation.
        set_dead_zone: Set a dead time that prohibits triggering within a certain time (trigger rejection). This is intended to exclude false trigger conditions. Can also be set to 0 to disable this feature.
        arm: Arm the PicoGlitcher and wait for the trigger condition. The trigger condition can either be when the reset on the target is released or when a certain pattern is observed in the serial communication. 
        block: Block until trigger condition is met. Raises an exception if times out.
    """
    def __init__(self):
        """
        Default constructor.
        Initializes the PicoGlitcher with the default configuration.
        - Disables `VTARGET`
        - Enables the low-power MOSFET for glitching
        - Configures the PicoGlitcher to use the rising-edge triggger condition.
        """
        self.sm1 = None
        self.sm2 = None
        self.sm3 = None
        self.frequency = None
        self.trigger_mode = "tio"
        self.glitch_mode = "crowbar"
        self.baudrate = 115200
        self.number_of_bits = 8
        self.set_frequency(200_000_000) # overclocking supposedly works, script runs also with 270_000_000
        # LED
        self.led = Pin("LED", Pin.OUT)
        self.led.low()
        # VTARGET_EN (active low)
        self.pin_vtarget_en = Pin(VTARGET_EN, Pin.OUT, Pin.PULL_UP)
        self.pin_vtarget_en.high()
        # RESET
        self.pin_reset = Pin(RESET, Pin.OUT, Pin.PULL_UP)
        self.pin_reset.low()
        # GLITCH_EN
        self.pin_glitch_en = Pin(GLITCH_EN, Pin.OUT, Pin.PULL_DOWN)
        self.pin_glitch_en.low()
        # TRIGGER
        self.pin_trigger = Pin(TRIGGER, Pin.IN, Pin.PULL_DOWN)
        # HP_GLITCH
        self.pin_hpglitch = Pin(HP_GLITCH, Pin.OUT, Pin.PULL_DOWN)
        self.pin_hpglitch.low()
        # LP_GLITCH
        self.pin_lpglitch = Pin(LP_GLITCH, Pin.OUT, Pin.PULL_DOWN)
        self.pin_lpglitch.low()
        # which glitching transistor to use. Default: lpglitch
        self.pin_glitch = self.pin_lpglitch
        # pins for pulse shaping (only hardware version 2)
        if hardware_version[0] >= 2:
            self.pin_mux1 = Pin(MUX1, Pin.OUT, Pin.PULL_DOWN)
            self.pin_mux0 = Pin(MUX0, Pin.OUT, Pin.PULL_DOWN)
            self.pin_mux1.low()
            self.pin_mux0.low()
        # standard dead zone after power down
        self.dead_time = 0.0
        self.pin_condition = self.pin_vtarget_en
        self.condition = 0

    def get_firmware_version(self) -> list:
        """
        Get the current firmware version. Can be used to check if the current version is compatible with findus.

        Returns:
            Returns the current firmware version.
        """
        print(software_version)
        return software_version

    def set_frequency(self, frequency:int = 200_000_000):
        """
        Set the CPU frequency of the Raspberry Pi Pico.
        
        Parameters:
            frequency: the CPU frequency.
        """
        machine.freq(frequency)
        self.frequency = machine.freq()

    def get_frequency(self) -> int:
        """
        Get the current CPU frequency of the Raspberry Pi Pico.
        
        Returns:
            Returns the CPU frequency.
        """
        print(machine.freq())
        return machine.freq()

    def set_trigger(self, mode:str = "tio", pin_trigger:str = "default"):
        """
        Configures the PicoGlitcher which triggger mode to use.
        In "tio"-mode, the PicoGlitcher triggers on a rising edge on the `TRIGGER` pin.
        If "uart"-mode is chosen, the PicoGlitcher listens on the `TRIGGER` pin and triggers if a specific byte pattern in the serial communication is observed.

        Parameters:
            mode: The trigger mode to use. Either "tio" or "uart".
            pin_trigger: The trigger pin to use. Can be either "default" or "alt". For hardware version 2 options "ext1" or "ext2" can also be chosen.
        """
        self.trigger_mode = mode
        if pin_trigger == "default":
            self.pin_trigger = Pin(TRIGGER, Pin.IN, Pin.PULL_DOWN)
        elif pin_trigger == "alt":
            self.pin_trigger = Pin(ALT_TRIGGER, Pin.IN, Pin.PULL_DOWN)
        elif pin_trigger == "ext1":
            self.pin_trigger = Pin(EXT1, Pin.IN, Pin.PULL_DOWN)
        elif pin_trigger == "ext2":
            self.pin_trigger = Pin(EXT2, Pin.IN, Pin.PULL_DOWN)

    def set_baudrate(self, baud:int = 115200):
        """
        Set the baudrate of the UART communication in UART-trigger mode.

        Parameters:
            baud: The baudrate to use.
        """
        self.baudrate = baud

    def set_number_of_bits(self, number_of_bits:int = 8):
        """
        Set the number of bits of the UART communication in UART-trigger mode.
        
        Parameters:
            number_of_bits: The number of bits of the UART payload to use.
        """
        self.number_of_bits = number_of_bits

    def set_pattern_match(self, pattern:int):
        """
        Configure the PicoGlitcher to trigger when a specific byte pattern is observed on the RX line (`TRIGGER` pin).

        Parameters:
            pattern: Byte pattern that is transmitted on the serial lines to trigger on. For example `0x11`.
        """
        self.pattern = pattern

    def enable_vtarget(self):
        """
        Enable `VTARGET` output. Activates the PicoGlitcher's power supply for the target.
        """
        self.pin_vtarget_en.low()

    def disable_vtarget(self):
        """
        Disables `VTARGET` output. Disables the PicoGlitcher's power supply for the target.
        """
        self.pin_vtarget_en.high()

    def power_cycle_target(self, power_cycle_time:float = 0.2):
        """
        Power cycle the target via the PicoGlitcher `VTARGET` output.
        
        Parameters:
            power_cycle_time: Time how long the power supply is cut.
        """
        self.disable_vtarget()
        time.sleep(power_cycle_time)
        self.enable_vtarget()

    def reset_target(self):
        """
        Reset the target via the PicoGlitcher's `RESET` output.
        """
        self.pin_reset.low()

    def release_reset(self):
        """
        Release the reset on the target via the PicoGlitcher's `RESET` output.
        """
        self.pin_reset.high()

    def reset(self, reset_time:float = 0.01):
        """
        Reset the target via the PicoGlitcher's `RESET` output, release the reset on the target after a certain time.
        
        Parameters:
            reset_time: Time how long the target is held in reset.
        """
        self.reset_target()
        time.sleep(reset_time)
        self.release_reset()

    def set_lpglitch(self):
        """
        Enable the low-power crowbar MOSFET for glitch generation.

        The glitch output is an SMA-connected output line that is normally connected to a target's power rails. If this setting is enabled, a low-powered MOSFET shorts the power-rail to ground when the glitch module's output is active.
        """
        self.glitch_mode = "crowbar"
        self.pin_glitch = self.pin_lpglitch

    def set_hpglitch(self):
        """
        Enable the high-power crowbar MOSFET for glitch generation.

        The glitch output is an SMA-connected output line that is normally connected to a target's power rails. If this setting is enabled, a low-powered MOSFET shorts the power-rail to ground when the glitch module's output is active.
        """
        self.glitch_mode = "crowbar"
        self.pin_glitch = self.pin_hpglitch

    def set_pulse_shaping(self):
        """
        TODO
        """
        self.glitch_mode = "pulse"
        self.pin_glitch = self.pin_mux1

    def set_dead_zone(self, dead_time:float = 0, pin_condition:str = "default"):
        """
        Set a dead time that prohibits triggering within a certain time (trigger rejection). This is intended to exclude false trigger conditions. Can also be set to 0 to disable this feature.
        
        Parameters:
            dead_time: Rejection time during triggering is disabled.
            pin_condition: Can either be "default", "power" or "reset". In "power" mode, the `TRIGGER` input is connected to the target's power and the rejection time is measured after power doen. In "reset" mode, the `TRIGGER` input is connected to the `RESET` line and the rejection time is measured after the device is reset. These modes imply different internal conditions to configure the dead time. If "default" is chosen, effectively no dead time is active.
        """
        if pin_condition == "default":
            self.pin_condition = self.pin_glitch_en
            # wait until GLITCH_EN is high (if armed)
            self.condition = 1
        elif pin_condition == "power":
            self.pin_condition = self.pin_vtarget_en
            # wait until VTARGET_EN is high (meaning VTARGET is disabled)
            self.condition = 1
        elif pin_condition == "reset":
            self.pin_condition = self.pin_reset
            # wait until RESET is low
            self.condition = 0
        self.dead_time = dead_time

    def arm(self, delay:int, length:int):
        """
        Arm the PicoGlitcher and wait for the trigger condition. The trigger condition can either be when the reset on the target is released or when a certain pattern is observed in the serial communication. 

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            length: Length of the glitch in nano seconds. Expect a resolution of about 5 nano seconds.
        """
        self.release_reset()
        self.pin_hpglitch.low()
        self.pin_lpglitch.low()
        if hardware_version[0] >= 2:
            self.pin_mux1.low()
            self.pin_mux0.low()

        if self.glitch_mode == "crowbar":
            # state machine that emits the glitch if the trigger condition is met
            self.sm1 = StateMachine(1, glitch, freq=self.frequency, set_base=self.pin_glitch, sideset_base=self.pin_glitch_en)
            self.sm1.active(1)
            # push delay and length (in nano seconds) into the fifo of the statemachine
            self.sm1.put(delay // (1_000_000_000 // self.frequency))
            self.sm1.put(length // (1_000_000_000 // self.frequency))

        elif self.glitch_mode == "pulse":
            # state machine that emits the glitch if the trigger condition is met
            self.sm1 = StateMachine(1, pulse, freq=self.frequency, set_base=self.pin_glitch, sideset_base=self.pin_glitch_en)
            self.sm1.active(1)
            # push delay and length (in nano seconds) into the fifo of the statemachine
            self.sm1.put(delay // (1_000_000_000 // self.frequency))
            self.sm1.put(length // (1_000_000_000 // self.frequency))

        if self.trigger_mode == "tio":
            # state machine that checks the trigger condition
            self.sm2 = StateMachine(2, tio_trigger, freq=self.frequency, in_base=self.pin_trigger)
            self.sm2.active(1)

            # state machine that blocks for a specific time after a certain condition (dead time)
            sm3_func = None
            if self.condition == 1:
                sm3_func = block_rising_condition
            else:
                sm3_func = block_falling_condition
            self.sm3 = StateMachine(3, sm3_func, freq=self.frequency, in_base=self.pin_condition)
            self.sm3.active(1)
            # push dead time (in seconds) into the fifo of the statemachine
            self.sm3.put(int(self.dead_time * self.frequency))

        elif self.trigger_mode == "uart":
            # state machine that checks the trigger condition
            self.sm2 = StateMachine(2, uart_trigger, freq=self.baudrate * 8, in_base=self.pin_trigger)
            self.sm2.active(1)
            # push pattern into the fifo of the statemachine
            pattern = self.pattern << (32 - self.number_of_bits)
            self.sm2.put(pattern)
            # push number of bits into the fifo of the statemachine (self.number_of_bits - 1 is an optimization here)
            self.sm2.put(self.number_of_bits - 1)

    def block(self, timeout:float):
        """
        Block until trigger condition is met. Raises an exception if times out.
        
        Parameters:
            timeout: Time after the block is released.
        """
        if self.sm1 is not None:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.sm1.rx_fifo() > 0:
                    break
            if time.time() - start_time >= timeout:
                self.sm1.active(0)
                self.pin_glitch_en.low()
                raise Exception("Function execution timed out!")

    def get_sm2_output(self):
        if self.sm2 is not None:
            # pull the output of statemachine 2
            res = self.sm2.get()
            print(res)