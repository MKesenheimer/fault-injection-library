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

    # wait for irq in block_rising_condition or block_falling_condition state machine
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
    irq(block, 7)

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
    irq(block, 7)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def test():
    # block until dead time received
    pull(block)
    mov(x, osr)

    # get the content of x with function get_sm2_output()
    mov(isr, x)
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
        __init__: Default constructor. Initializes the PicoGlitcher with the default configuration.
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
        reset: Reset the target via the PicoGlitcher's `RESET` output, release the reset on the target after a certain time. Disables `GLITCH_EN` output after release.
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
        self.frequency = None
        self.trigger = "tio"
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
        self.dead_time = 0.0
        self.pin_condition = self.pin_vtarget_en
        self.condition = 0

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

    def set_trigger(self, trigger:str = "tio"):
        """
        Configures the PicoGlitcher which triggger condition to use.
        In "tio"-mode, the PicoGlitcher triggers on a rising edge on the `TRIGGER` pin. If "uart"-mode is chosen, the PicoGlitcher listens on the `TRIGGER` pin and triggers if a specific byte pattern in the serial communication is observed.

        Parameters:
            trigger: The trigger condition to use. Either "tio" or "uart".
        """
        self.trigger = trigger

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
        self.pin_glitch_en.low()

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
        Reset the target via the PicoGlitcher's `RESET` output, release the reset on the target after a certain time. Disables `GLITCH_EN` output after release.
        
        Parameters:
            reset_time: Time how long the target is held in reset.
        """
        self.reset_target()
        time.sleep(reset_time)
        self.release_reset()
        self.pin_glitch_en.low()

    def set_lpglitch(self):
        """
        Enable the low-power crowbar MOSFET for glitch generation.

        The glitch output is an SMA-connected output line that is normally connected to a target's power rails. If this setting is enabled, a low-powered MOSFET shorts the power-rail to ground when the glitch module's output is active.
        """
        self.pin_glitch = self.pin_lpglitch

    def set_hpglitch(self):
        """
        Enable the high-power crowbar MOSFET for glitch generation.

        The glitch output is an SMA-connected output line that is normally connected to a target's power rails. If this setting is enabled, a low-powered MOSFET shorts the power-rail to ground when the glitch module's output is active.
        """
        self.pin_glitch = self.pin_hpglitch

    def set_dead_zone(self, dead_time:float = 0, pin:str = "default"):
        """
        Set a dead time that prohibits triggering within a certain time (trigger rejection). This is intended to exclude false trigger conditions. Can also be set to 0 to disable this feature.
        
        Parameters:
            dead_time: Rejection time during triggering is disabled.
            pin: Can either be "default", "power" or "reset". In "power" mode, the `TRIGGER` input is connected to the target's power and the rejection time is measured after power doen. In "reset" mode, the `TRIGGER` input is connected to the `RESET` line and the rejection time is measured after the device is reset. These modes imply different internal conditions to configure the dead time. If "default" is chosen, no dead time is active.
        """
        if pin == "default":
            self.pin_condition = self.pin_glitch_en
            # wait until GLITCH_EN is high
            self.condition = 1
        elif pin == "power":
            self.pin_condition = self.pin_vtarget_en
            # wait until VTARGET_EN is high (meaning VTARGET is disabled)
            self.condition = 1
        elif pin == "reset":
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
            sm2_func = None
            if self.condition == 1:
                sm2_func = block_rising_condition
            else:
                sm2_func = block_falling_condition
            self.sm2 = StateMachine(2, sm2_func, freq=self.frequency, in_base=self.pin_condition)
            self.sm2.active(1)
            # push dead time (in seconds) into the fifo of the statemachine
            self.sm2.put(int(self.dead_time * self.frequency))
        
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
                raise Exception("Function execution timed out!")

    def get_sm2_output(self):
        if self.sm2 is not None:
            # pull the output of statemachine 2
            res = self.sm2.get()
            print(res)