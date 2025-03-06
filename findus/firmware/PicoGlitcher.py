# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

"""
This is the documentation of the PicoGlitcher module and all its classes.

Upload this module onto your Pico Glitcher. The classes and methods will become available through the pyboard interface.
"""

import machine
from rp2 import asm_pio, PIO, StateMachine
from machine import Pin
import time
import ujson
from FastADC import FastADC
import _thread

# load config
with open("config.json", "r") as file:
    config = ujson.load(file)

if config["hardware_version"][0] == 1:
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
elif config["hardware_version"][0] == 2:
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
    if config["mux_vinit"] == "GND":
        MUX1_INIT = 1
        MUX0_INIT = 1
        MUX1_PIO_INIT = PIO.OUT_HIGH
        MUX0_PIO_INIT = PIO.OUT_HIGH
        MUX_PIO_INIT = 0b11
    elif config["mux_vinit"] == "1.8":
        MUX1_INIT = 0
        MUX0_INIT = 1
        MUX1_PIO_INIT = PIO.OUT_LOW
        MUX0_PIO_INIT = PIO.OUT_HIGH
        MUX_PIO_INIT = 0b01
    elif config["mux_vinit"] == "VCC":
        MUX1_INIT = 0
        MUX0_INIT = 0
        MUX1_PIO_INIT = PIO.OUT_LOW
        MUX0_PIO_INIT = PIO.OUT_LOW
        MUX_PIO_INIT = 0b00
    else: # 3.3V
        MUX1_INIT = 1
        MUX0_INIT = 0
        MUX1_PIO_INIT = PIO.OUT_HIGH
        MUX0_PIO_INIT = PIO.OUT_LOW
        MUX_PIO_INIT = 0b10
    import AD910X
    from PulseGenerator import PulseGenerator

def irq_clear(sm):
  pass

@asm_pio(set_init=(PIO.OUT_LOW), sideset_init=(PIO.OUT_LOW), in_shiftdir=PIO.SHIFT_RIGHT)
def glitch():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until length received
    pull(block)
    mov(y, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 7).side(0b1)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # emit glitch at base pin
    set(pins, 0b1)
    label("length_loop")       
    jmp(y_dec, "length_loop")

    # stop glitch and disable pin_glitch_en
    set(pins, 0b0).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    irq(clear, 7)
    push(block)

@asm_pio(set_init=(PIO.OUT_HIGH), sideset_init=(PIO.OUT_LOW), in_shiftdir=PIO.SHIFT_RIGHT)
def pulse_shaping():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until total length of pulse received
    pull(block)
    mov(y, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 7).side(0b1)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # set trigger pin low (start pulse generator)
    set(pins, 0b0)
    label("length_loop")
    jmp(y_dec, "length_loop")

    # stop pulse and disable pin_glitch_en
    set(pins, 0b1).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    irq(clear, 7)
    push(block)

@asm_pio(set_init=(MUX0_PIO_INIT, MUX1_PIO_INIT), out_init=(MUX0_PIO_INIT, MUX1_PIO_INIT), sideset_init=(PIO.OUT_LOW), in_shiftdir=PIO.SHIFT_RIGHT, out_shiftdir=PIO.SHIFT_RIGHT)
def multiplex(MUX_PIO_INIT=MUX_PIO_INIT):
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until multiplexing config received
    pull(block)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 7).side(0b1)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # get the pulse length and pulse voltage and set the corresponding outputs
    set(x, 2)
    label("two_pulses")
    out(y, 14) # t = OSR >> 14
    #set(pindirs, 0b00) # disable pinout while shifting
    out(pins, 2) # v = OSR >> 2
    #set(pindirs, 0b11) # enable pinout again
    label("length_loop")
    jmp(y_dec, "length_loop")
    jmp(x_dec, "two_pulses")

    # pull the next config
    pull(block)

    # get the pulse length and pulse voltage and set the corresponding outputs
    set(x, 2)
    label("two_pulses2")
    out(y, 14) # t = OSR >> 14
    #set(pindirs, 0b00) # disable pinout while shifting
    out(pins, 2) # v = OSR >> 2
    #set(pindirs, 0b11) # enable pinout again
    label("length_loop2")
    jmp(y_dec, "length_loop2")
    jmp(x_dec, "two_pulses2")

    # reset and disable pin_glitch_en
    set(pins, MUX_PIO_INIT).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    irq(clear, 7)
    push(block)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def tio_trigger_with_dead_time_rising_edge():
    # wait for irq in block_rising_condition or block_falling_condition state machine (dead time)
    wait(1, irq, 6)

    # wait for rising edge on trigger pin
    wait(0, pin, 0)
    wait(1, pin, 0)

    # tell observed trigger
    # TODO: should block be removed?
    irq(block, 7)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def tio_trigger_with_dead_time_falling_edge():
    # wait for irq in block_rising_condition or block_falling_condition state machine (dead time)
    wait(1, irq, 6)

    # wait for falling edge on trigger pin
    wait(1, pin, 0)
    wait(0, pin, 0)

    # tell observed trigger
    # TODO: should block be removed?
    irq(block, 7)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def edge_trigger_rising_edge():
    # block until number of edges received
    pull(block)
    mov(x, osr)

    label("edge_count_loop")

    # wait for rising edge on trigger pin
    wait(0, pin, 0)
    wait(1, pin, 0)

    # decrease x and jump to the beginning of the loop
    jmp(x_dec, "edge_count_loop")

    # tell observed trigger
    # TODO: should block be removed?
    irq(block, 7)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def edge_trigger_falling_edge():
    # block until number of edges received
    pull(block)
    mov(x, osr)

    label("edge_count_loop")

    # wait for falling edge on trigger pin
    wait(1, pin, 0)
    wait(0, pin, 0)

    # decrease x and jump to the beginning of the loop
    jmp(x_dec, "edge_count_loop")

    # tell observed trigger
    # TODO: should block be removed?
    irq(block, 7)

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

    # tell execution finished
    # TODO: can block be removed?
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

    # tell execution finished
    # TODO: can block be removed?
    irq(block, 6)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT)
def test():
    # block until dead time received
    pull(block)
    #mov(x, osr)
    out(x, 18)

    # get the content of x with function get_sm1_output()
    mov(isr, x)
    push(block)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT, out_shiftdir=PIO.SHIFT_LEFT)
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
    #set(y, BITS - 1) [10]
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
    # TODO: can "block" be removed?
    irq(block, 7)

    # wrap around
    jmp("start")

@micropython.asm_thumb
def wait_irq7():
    # mov 0xE000E200 to r0
    mov(r1, 0xE0)
    mov(r2, 16)
    lsl(r1, r2) # r0 = 0xE00000
    mov(r2, 0xE2)
    orr(r1, r2) # r0 = 0xE000E2
    mov(r2, 8)
    lsl(r1, r2) # r0 = 0xE000E200

    label(loop)
    ldr(r0, [r1, 0]) # Load NVIC_ISPR (interrupt pending register)
    mov(r2, 0b1000) # irq7 is bit 3 of NVIC_ISPR
    tst(r0, r2) # r0 & r2
    beq(loop) # if r0 & r2 == 0 -> IRQ7 bit not set

class PicoGlitcher():
    """
    Class that contains the code to access the hardware of the Pico Glitcher.
    """
    def __init__(self):
        """
        Default constructor.
        Initializes the Pico Glitcher with the default configuration.
        - Disables `VTARGET`
        - Enables the low-power MOSFET for glitching
        - Configures the Pico Glitcher to use the rising-edge triggger condition.
        """
        self.sm0 = None
        self.sm1 = None
        self.sm2 = None
        self.frequency = None
        self.trigger_mode = "tio"
        self.glitch_mode = "crowbar"
        self.baudrate = 115200
        self.number_of_bits = 8

        # read config
        with open("config.json", "r") as file:
            self.config = ujson.load(file)

        if self.config["hardware_version"][0] == 1:
            # overclocking supposedly works, script runs also with 270_000_000
            self.set_frequency(200_000_000)
        elif self.config["hardware_version"][0] == 2:
            self.set_frequency(250_000_000)
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
        self.trigger_inverting = False
        # HP_GLITCH
        self.pin_hpglitch = Pin(HP_GLITCH, Pin.OUT, Pin.PULL_DOWN)
        self.pin_hpglitch.low()
        # LP_GLITCH
        self.pin_lpglitch = Pin(LP_GLITCH, Pin.OUT, Pin.PULL_DOWN)
        self.pin_lpglitch.low()
        # which glitching transistor to use. Default: lpglitch
        self.pin_glitch = self.pin_lpglitch
        # standard dead zone after power down
        self.dead_time = 0.0
        self.pin_condition = self.pin_vtarget_en
        self.condition = "rising"
        self.number_of_edges = 1
        # pins for multiplexing and pulse-shaping (only hardware version 2)
        if self.config["hardware_version"][0] >= 2:
            self.pin_mux1 = Pin(MUX1, Pin.OUT, Pin.PULL_DOWN)
            self.pin_mux0 = Pin(MUX0, Pin.OUT, Pin.PULL_DOWN)
            self.pin_mux1.value(MUX1_INIT)
            self.pin_mux0.value(MUX0_INIT)
            # lsb: GPIO0 -> MUX1
            # msb: GPIO1 -> MUX0
            # 0b00: IN1 = 1: VCC
            # 0b01: IN3 = 1: +1V8
            # 0b10: IN2 = 1: +3V3
            # 0b11: IN4 = 1: GND
            self.voltage_map = {"VCC": 0b00, "1.8": 0b01, "3.3": 0b10, "GND": 0b11}
            # Pulse shaping expansion board related stuff
            self.ad910x = AD910X.AD910X()
            self.ad910x.reset()
            self.ad910x.init()
            self.pin_ps_trigger = self.ad910x.get_trigger_pin()
            self.pulse_generator = PulseGenerator(vhigh=self.config["ps_offset"], factor=self.config["ps_factor"])
            # analog digital converter
            self.fastadc = FastADC()
            self.fastsamples = self.fastadc.init_array()
            self.core1_stopped = True
            # gpio outputs (are configured later as required)
            self.pin_gpios = {}

    def waveform_generator(self, frequency:int = AD910X.DEFAULT_FREQUENCY, gain:float = AD910X.DEFAULT_GAIN, waveid:int = AD910X.WAVE_TRIANGLE):
        if self.config["hardware_version"][0] < 2:
            raise Exception("Pulse-shaping not implemented in hardware version 1.")
        if waveid < AD910X.WAVE_SINE or waveid > AD910X.WAVE_NEGATIVE_SAWTOOTH:
            raise Exception("Wave-id not supported. Choose one of [0, 1, 2, 3, 4].")
        self.ad910x.set_frequency(frequency)
        self.ad910x.set_gain(gain)
        self.ad910x.set_wave_output(waveid)

    def get_firmware_version(self) -> list[int]:
        """
        Get the current firmware version. Can be used to check if the current version is compatible with findus.

        Returns:
            Returns the current firmware version.
        """
        print(self.config["software_version"])
        return self.config["software_version"]

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

    def set_trigger(self, mode:str = "tio", pin_trigger:str = "default", edge_type:str = "rising"):
        """
        Configures the Pico Glitcher which triggger mode to use.
        In "tio"-mode, the Pico Glitcher triggers on a rising edge on the `TRIGGER` pin.
        If "uart"-mode is chosen, the Pico Glitcher listens on the `TRIGGER` pin and triggers if a specific byte pattern in the serial communication is observed. In "edge"-mode, the Pico Glitcher counts the number of edges and triggers if a certain number of edges were observed. The parameter `edge_type` should be ignored if "uart"-mode is selected.

        Parameters:
            mode: The trigger mode to use. Either "tio" or "uart".
            pin_trigger: The trigger pin to use. Can be either "default" or "alt". For hardware version 2 options "ext1" or "ext2" can also be chosen.
            edge_type: Trigger on the "rising" (default) or "falling" edge.
        """
        self.trigger_mode = mode
        if pin_trigger == "default":
            self.pin_trigger = Pin(TRIGGER, Pin.IN, Pin.PULL_DOWN)
            if edge_type == "rising":
                self.trigger_inverting = False
            else:
                self.trigger_inverting = True
        elif pin_trigger == "alt":
            self.pin_trigger = Pin(ALT_TRIGGER, Pin.IN, Pin.PULL_DOWN)
            if edge_type == "rising":
                self.trigger_inverting = False
            else:
                self.trigger_inverting = True
        elif pin_trigger == "ext1":
            self.pin_trigger = Pin(EXT1, Pin.IN, Pin.PULL_DOWN)
            if edge_type == "rising":
                self.trigger_inverting = True
            else:
                self.trigger_inverting = False
        elif pin_trigger == "ext2":
            self.pin_trigger = Pin(EXT2, Pin.IN, Pin.PULL_DOWN)
            if edge_type == "rising":
                self.trigger_inverting = True
            else:
                self.trigger_inverting = False

    def set_number_of_edges(self, number_of_edges:int = 2):
        """
        Set the number of edges after which the Pico Glitcher triggers in edge-counting trigger mode.

        Parameters:
            number_of_edges: The number of edges after which the Pico Glitcher triggers.
        """
        self.number_of_edges = number_of_edges

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
        Configure the Pico Glitcher to trigger when a specific byte pattern is observed on the RX line (`TRIGGER` pin).

        Parameters:
            pattern: Byte pattern that is transmitted on the serial lines to trigger on. For example `0x11`.
        """
        self.pattern = pattern

    def enable_vtarget(self):
        """
        Enable `VTARGET` output. Activates the Pico Glitcher's power supply for the target.
        """
        self.pin_vtarget_en.low()

    def disable_vtarget(self):
        """
        Disables `VTARGET` output. Disables the Pico Glitcher's power supply for the target.
        """
        self.pin_vtarget_en.high()

    def power_cycle_target(self, power_cycle_time:float = 0.2):
        """
        Power cycle the target via the Pico Glitcher `VTARGET` output.
        
        Parameters:
            power_cycle_time: Time how long the power supply is cut.
        """
        self.disable_vtarget()
        time.sleep(power_cycle_time)
        self.enable_vtarget()

    def reset_target(self):
        """
        Reset the target via the Pico Glitcher's `RESET` output.
        """
        self.pin_reset.low()

    def release_reset(self):
        """
        Release the reset on the target via the Pico Glitcher's `RESET` output.
        """
        self.pin_reset.high()

    def reset(self, reset_time:float = 0.01):
        """
        Reset the target via the Pico Glitcher's `RESET` output, release the reset on the target after a certain time.
        
        Parameters:
            reset_time: Time how long the target is held in reset.
        """
        self.reset_target()
        time.sleep(reset_time)
        self.release_reset()

    def configure_gpio_out(self, pin_number:int):
        # TODO: check if pin is already in use
        self.pin_gpios[pin_number] = Pin(pin_number, Pin.OUT, Pin.PULL_DOWN)

    def set_gpio(self, pin_number:int, value:int):
        try:
            self.pin_gpios[pin_number].value(value)
        except KeyError:
            self.configure_gpio_out(pin_number)
            self.pin_gpios[pin_number].value(value)

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

    def set_multiplexing(self):
        """
        Enables the multiplexing mode of the Pico Glitcher version 2 to switch between different voltage levels.
        """
        if self.config["hardware_version"][0] < 2:
            raise Exception("Multiplexing not implemented in hardware version 1.")
        self.glitch_mode = "mul"
        self.pin_glitch = self.pin_mux1

    def set_pulseshaping(self, vinit=1.8):
        """
        Enables the pulse-shaping mode of the Pico Glitcher version 2 to emit a pre-defined voltage pulse on the Pulse Shaping expansion board.
        """
        if self.config["hardware_version"][0] < 2:
            raise Exception("Pulse-shaping not implemented in hardware version 1.")
        self.glitch_mode = "pul"
        self.pin_glitch = self.pin_ps_trigger

        # Configure the AD9102
        self.pulse_generator.set_offset(vinit)
        self.ad910x.set_frequency(self.pulse_generator.get_frequency())
        self.ad910x.set_gain(1.5)
        #self.ad910x.set_offset(2048)
        # configure the AD9102 to emit an oneshot pulse
        self.ad910x.set_pulse_output_oneshot()

    def do_calibration(self, vhigh:float):
        """
        Emit a calibration pulse with that can be used to determine `vhigh` and `vlow`. These parameters are used to calculate the offset and gain parameters of the DAC.

        Parameters:
            vhigh: The initial voltage to perform the calibration with. Default is `1V`.
        """
        self.set_pulseshaping(vhigh)
        pulse = self.pulse_generator.calibration_pulse()
        self.__arm_pulseshaping(delay=100, pulse=pulse)
        self.reset(0.01)

    def apply_calibration(self, vhigh:float, vlow:float, store:bool = True):
        """
        Calculate and store the offset and gain parameters that were determined by the calibration routine. These values are stored in `config.json` and must be re-calculated if the config is overwritten.

        Parameters:
            vhigh: The maximum voltage of the calibration voltage trace.
            vlow: The minimum voltage of the calibration voltage trace.
            store: wether to store the offset and gain factor in the Pico Glitcher configuration.
        """
        factor = 1/(vhigh - vlow)
        self.pulse_generator.set_calibration(vhigh, factor)
        if store:
            self.__change_config("ps_offset", vhigh)
            self.__change_config("ps_factor", factor)

    def set_dead_zone(self, dead_time:float = 0, pin_condition:str = "default", condition:str = "rising"):
        """
        Set a dead time that prohibits triggering within a certain time (trigger rejection). This is intended to exclude false trigger conditions. Can also be set to 0 to disable this feature.
        
        Parameters:
            dead_time: Rejection time during triggering is disabled.
            pin_condition: Can either be "default", "power", "reset" or a GPIO pin number (for example "4", "5" or "6"). In "power" mode, the `TRIGGER` input is connected to the target's power and the rejection time is measured after power doen. In "reset" mode, the `TRIGGER` input is connected to the `RESET` line and the rejection time is measured after the device is reset. These modes imply different internal conditions to configure the dead time. If "default" is chosen, effectively no dead time is active.
            condition: Can either be "falling" or "rising". The `dead_time` is measured on the pin `pin_condition` after the specified condition (falling- or rising edge). For example, a good choice is "rising" for the "default" configuration, "rising" for the "power" configuration and "falling" for the "reset" configuration.
        """
        if pin_condition == "default":
            self.pin_condition = self.pin_glitch_en
        elif pin_condition == "power":
            self.pin_condition = self.pin_vtarget_en
        elif pin_condition == "reset":
            self.pin_condition = self.pin_reset
        elif pin_condition.isdigit():
            pin_number = int(pin_condition)
            self.configure_gpio_out(pin_number)
            self.pin_condition = self.pin_gpios[pin_number]
        #print(f"self.pin_condition = {self.pin_condition}")
        self.dead_time = dead_time
        self.condition = condition

    def __arm_common(self):
        if self.trigger_mode == "tio":
            sm1_func = None
            if not self.trigger_inverting:
                sm1_func = tio_trigger_with_dead_time_rising_edge
            else:
                sm1_func = tio_trigger_with_dead_time_falling_edge
            # state machine that checks the trigger condition
            self.sm1 = StateMachine(1, sm1_func, freq=self.frequency, in_base=self.pin_trigger)

            # state machine that blocks for a specific time after a certain condition (dead time)
            sm2_func = None
            if self.condition == "rising":
                sm2_func = block_rising_condition
            else:
                sm2_func = block_falling_condition
            self.sm2 = StateMachine(2, sm2_func, freq=self.frequency, in_base=self.pin_condition)
            # push dead time (in seconds) into the fifo of the statemachine
            self.sm2.put(int(self.dead_time * self.frequency))

        elif self.trigger_mode == "edge":
            sm1_func = None
            if not self.trigger_inverting:
                sm1_func = edge_trigger_rising_edge
            else:
                sm1_func = edge_trigger_falling_edge
            # state machine that checks the trigger condition
            self.sm1 = StateMachine(1, sm1_func, freq=self.frequency, in_base=self.pin_trigger)
            self.sm1.put(self.number_of_edges - 1)

        elif self.trigger_mode == "uart":
            # state machine that checks the trigger condition
            self.sm1 = StateMachine(1, uart_trigger, freq=self.baudrate * 8, in_base=self.pin_trigger)
            # push pattern into the fifo of the statemachine
            pattern = self.pattern << (32 - self.number_of_bits)
            self.sm1.put(pattern)
            # push number of bits into the fifo of the statemachine (self.number_of_bits - 1 is an optimization here)
            self.sm1.put(self.number_of_bits - 1)

        if self.sm0 is not None:
            self.sm0.irq(handler=irq_clear)
            self.sm0.active(1)
        if self.sm1 is not None:
            self.sm1.irq(handler=irq_clear)
            self.sm1.active(1)
        if self.sm2 is not None:
            self.sm2.irq(handler=irq_clear)
            self.sm2.active(1)

    def arm(self, delay:int, length:int):
        """
        Arm the Pico Glitcher and wait for the trigger condition. The trigger condition can either be when the reset on the target is released or when a certain pattern is observed in the serial communication.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            length: Length of the glitch in nano seconds. Expect a resolution of about 5 nano seconds.
        """
        self.release_reset()
        self.pin_hpglitch.low()
        self.pin_lpglitch.low()

        # state machine that emits the glitch if the trigger condition is met
        self.sm0 = StateMachine(0, glitch, freq=self.frequency, set_base=self.pin_glitch, sideset_base=self.pin_glitch_en)
        # push delay and length (in nano seconds) into the fifo of the statemachine
        self.sm0.put(int(delay) // (1_000_000_000 // self.frequency))
        self.sm0.put(int(length) // (1_000_000_000 // self.frequency))

        self.__arm_common()

    def arm_multiplexing(self, delay:int, mul_config:dict):
        """
        Arm the Pico Glitcher in multiplexing mode and wait for the trigger condition.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            mul_config: The dictionary for the multiplexing profile with pairs of identifiers and values. For example, this could be `{"t1": 10, "v1": "GND", "t2": 20, "v2": "1.8", "t3": 30, "v3": "GND", "t4": 40, "v4": "1.8"}`. Meaning that when triggered, a GND-voltage pulse with duration of `10ns` is emitted, followed by a +1.8V step with duration of `20ns` and so on.
        """
        if self.config["hardware_version"][0] < 2:
            raise Exception("Multiplexing not implemented in hardware version 1.")

        self.pin_mux1.value(MUX1_INIT)
        self.pin_mux0.value(MUX0_INIT)

        # state machine that emits the glitch if the trigger condition is met (part 1)
        self.sm0 = StateMachine(0, multiplex, freq=self.frequency, set_base=self.pin_glitch, out_base=self.pin_glitch, sideset_base=self.pin_glitch_en)
        # push multiplexing shape config into the fifo of the statemachine
        self.sm0.put(int(delay) // (1_000_000_000 // self.frequency))
        try:
            t1 = int(mul_config["t1"]) // (1_000_000_000 // self.frequency)
            v1 = self.voltage_map[mul_config["v1"]]
        except Exception as _:
            t1 = 0
            v1 = MUX_PIO_INIT
        try:
            t2 = int(mul_config["t2"]) // (1_000_000_000 // self.frequency)
            v2 = self.voltage_map[mul_config["v2"]]
        except Exception as _:
            t2 = 0
            v2 = MUX_PIO_INIT
        config = v2 << 30 | t2 << 16 | v1 << 14 | t1
        self.sm0.put(config)
        # push the next multiplexing shape config into the fifo of the statemachine
        try:
            t3 = int(mul_config["t3"]) // (1_000_000_000 // self.frequency)
            v3 = self.voltage_map[mul_config["v3"]]
        except Exception as _:
            t3 = 0
            v3 = MUX_PIO_INIT
        try:
            t4 = int(mul_config["t4"]) // (1_000_000_000 // self.frequency)
            v4 = self.voltage_map[mul_config["v4"]]
        except Exception as _:
            t4 = 0
            v4 = MUX_PIO_INIT
        config = v4 << 30 | t4 << 16 | v3 << 14 | t3
        self.sm0.put(config)

        self.__arm_common()

    def arm_pulseshaping_from_config(self, delay:int, ps_config:list[list[float]]):
        """
        Arm the Pico Glitcher and wait for the trigger condition. The pulse is defined via a configuration similar to multiplexing (without interpolation):

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            ps_config: The pulse configuration given as a list of time deltas and voltage values.
        """
        pulse = self.pulse_generator.pulse_from_config(ps_config)
        self.__arm_pulseshaping(delay, pulse)

    def arm_pulseshaping_from_spline(self, delay:int, xpoints:list[int], ypoints:list[float]):
        """
        Arm the Pico Glitcher and wait for the trigger condition. The pulse definition is given by time and voltage points. Intermediate values are interpolated.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            xpoints: A list of time points (in nanoseconds) where voltage changes occur.
            ypoints: The corresponding voltage levels at each time point.
        """
        pulse = self.pulse_generator.pulse_from_spline(xpoints, ypoints)
        self.__arm_pulseshaping(delay, pulse)

    def arm_pulseshaping_from_lambda(self, delay:int, ps_lambda, pulse_number_of_points:int):
        """
        Arm the Pico Glitcher and wait for the trigger condition. Generate the pulse from a lambda function depending on the time.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            ps_lambda: A lambda function that defines the glitch at certain times. Must be given as string which is processed by the Pico Glitcher at runtime.
            pulse_number_of_points: The approximate length of the pulse. This is needed to constrain the pulse and to save computing time.
        """
        pulse = self.pulse_generator.pulse_from_lambda(ps_lambda, pulse_number_of_points)
        self.__arm_pulseshaping(delay, pulse)

    def arm_pulseshaping_from_list(self, delay:int, pulse:list[int]):
        """
        Arm the Pico Glitcher and wait for the trigger condition. Genereate the pulse from a raw array of values.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            pulse: A raw list of points that define the pulse. No calibration and no constraints are applied to the list. The list is forwarded directly to the DAC.
        """
        pulse = self.pulse_generator.pulse_from_list(pulse)
        self.__arm_pulseshaping(delay, pulse)

    def __arm_pulseshaping(self, delay:int, pulse:list[int]):
        if self.config["hardware_version"][0] < 2:
            raise Exception("Multiplexing not implemented in hardware version 1.")

        # disable pulse output
        self.pin_ps_trigger.high()
        # load the pulse into AD9102 SRAM
        self.ad910x.write_sram_from_start(pulse)
        self.ad910x.update_sram(len(pulse))

        # state machine that pulls the ps_trigger pin to low if the trigger condition is met
        self.sm0 = StateMachine(0, pulse_shaping, freq=self.frequency, set_base=self.pin_glitch, out_base=self.pin_glitch, sideset_base=self.pin_glitch_en)
        # push delay (in nano seconds) into the fifo of the statemachine
        self.sm0.put(int(delay) // (1_000_000_000 // self.frequency))
        maxlength = 10_000 # TODO: control this by an argument or the pulse length
        self.sm0.put(maxlength // (1_000_000_000 // self.frequency))

        self.__arm_common()
        #print(pulse)

    def block(self, timeout:float):
        """
        Block until trigger condition is met. Raises an exception if times out.
        
        Parameters:
            timeout: Time after the block is released.
        """
        if self.sm0 is not None:
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.sm0.rx_fifo() > 0:
                    break
            if time.time() - start_time >= timeout:
                self.sm0.active(0)
                self.pin_glitch_en.low()
                self.core1_stopped = True
                raise Exception("Function execution timed out!")

    def get_sm1_output(self):
        if self.sm1 is not None:
            # pull the output of statemachine 2
            res = self.sm1.get()
            print(res)

    def __change_config(self, key:str, value:int|float|str):
        """
        Change the content of the configuration file `config.json`. Note that the value to be changed must already exist.

        Parameters:
            key: Key of value to be replaced.
            value: Value to be set.
        """
        with open("config.json", "r") as file:
            config = ujson.load(file)

        # change value
        config[key] = value
        # dump config to file
        with open("config.json", "w") as file:
            ujson.dump(config, file)

        # read back
        with open("config.json", "r") as file:
            config = ujson.load(file)
        print(config)

    def change_config_and_reset(self, key:str, value:int|float|str):
        """
        Change the content of the configuration file `config.json`. Note that the value to be changed must already exist. Reset the Pico Glitcher.

        Parameters:
            key: Key of value to be replaced.
            value: Value to be set.
        """
        self.__change_config(key, value)
        machine.soft_reset()
        #machine.reset()

    def hard_reset(self):
        """
        Perform a hard reset of the Pico Glitcher (Raspberry Pi Pico).
        """
        machine.reset()

    @micropython.native
    def __poll_fast_adc(self):
        self.core1_stopped = False
        # wait for trigger condition
        wait_irq7()
        # this code runs with ~2us per sample -> 450 ksps
        self.fastsamples = self.fastadc.read()
        self.core1_stopped = True

    def arm_adc(self):
        """
        Arm the ADC on pin 26 and capture ADC samples if the trigger condition is met. On Pico Glitcher hardware version 1, the separate SMA connector labeled `Analog` can be used to measure analog voltage traces. On revision 2, the analog input is directly connected to the `GLITCH` line.
        """
        if self.core1_stopped:
            _thread.start_new_thread(self.__poll_fast_adc, ())

    def get_adc_samples(self):
        """
        Read back the captured ADC samples.
        """
        timeout = 1
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.core1_stopped:
                break
        if time.time() - start_time >= timeout:
            raise Exception("ADC timed out!")
        #while not self.core1_stopped:
        #    pass
        self.core1_stopped = True
        print(self.fastsamples)

    def configure_adc(self, number_of_samples:int = 1024, sampling_freq:int = 500_000):
        """
        Configure the onboard ADC of the Pico Glitcher.

        Parameters:
            number_of_samples: The number of samples to capture after triggering.
            sampling_freq: The sampling frequency of the ADC. `500 kSPS` is the maximum.
        """
        self.fastadc.configure_adc(number_of_samples, sampling_freq)
        self.fastsamples = self.fastadc.init_array()

    def stop_core1(self):
        """
        Stop execution on the second core of the Pico Glitcher (Raspberry Pi Pico).
        """
        self.core1_stopped = True
