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
from machine import Pin, SPI
import time
import ujson

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
    PS_TRIGGER = 5
    PS_RESET = 6
    PS_SPI_MISO = 16
    PS_SPI_CS = 17
    PS_SPI_SCK = 18
    PS_SPI_MOSI = 19

REG_SPI_CONFIG     = 0x0000
REG_POWER_CONFIG   = 0x0001
REG_CLOCK_CONFIG   = 0x0002
REG_REF_ADJ        = 0x0003
REG_DAC4_AGAIN     = 0x0004
REG_DAC3_AGAIN     = 0x0005
REG_DAC2_AGAIN     = 0x0006
REG_DAC1_AGAIN     = 0x0007
REG_DACX_RANGE     = 0x0008
REG_DAC4_RSET      = 0x0009
REG_DAC3_RSET      = 0x000A
REG_DAC2_RSET      = 0x000B
REG_DAC1_RSET      = 0x000C
REG_CAL_CONFIG     = 0x000D
REG_COMP_OFFSET    = 0x000E
REG_RAM_UPDATE     = 0x001D
REG_PAT_STATUS     = 0x001E
REG_PAT_TYPE       = 0x001F
REG_PATTERN_DLY    = 0x0020
REG_DAC4_DOF       = 0x0022
REG_DAC3_DOF       = 0x0023
REG_DAC2_DOF       = 0x0024
REG_DAC1_DOF       = 0x0025
REG_WAV43_CONFIG   = 0x0026
REG_WAV21_CONFIG   = 0x0027
REG_PAT_TIMEBASE   = 0x0028
REG_PAT_PERIOD     = 0x0029
REG_DAC43_PATX     = 0x002A
REG_DAC21_PATX     = 0x002B
REG_DOUT_START_DLY = 0x002C
REG_DOUT_CONFIG    = 0x002D
REG_DAC4_CST       = 0x002E
REG_DAC3_CST       = 0x002F
REG_DAC2_CST       = 0x0030
REG_DAC1_CST       = 0x0031
REG_DAC4_DGAIN     = 0x0032
REG_DAC3_DGAIN     = 0x0033
REG_DAC2_DGAIN     = 0x0034
REG_DAC1_DGAIN     = 0x0035
REG_SAW43_CONFIG   = 0x0036
REG_SAW21_CONFIG   = 0x0037
REG_DDS_TW32       = 0x003E
REG_DDS_TW1        = 0x003F
REG_DDS4_PW        = 0x0040
REG_DDS3_PW        = 0x0041
REG_DDS2_PW        = 0x0042
REG_DDS1_PW        = 0x0043
REG_TRIG_TW_SEL    = 0x0044
REG_DDSX_CONFIG    = 0x0045
REG_TW_RAM_CONFIG  = 0x0047
REG_START_DLY4     = 0x0050
REG_START_ADDR4    = 0x0051
REG_STOP_ADDR4     = 0x0052
REG_DDS_CYC4       = 0x0053
REG_START_DLY3     = 0x0054
REG_START_ADDR3    = 0x0055
REG_STOP_ADDR3     = 0x0056
REG_DDS_CYC3       = 0x0057
REG_START_DLY2     = 0x0058
REG_START_ADDR2    = 0x0059
REG_STOP_ADDR2     = 0x005A
REG_DDS_CYC2       = 0x005B
REG_START_DLY1     = 0x005C
REG_START_ADDR1    = 0x005D
REG_STOP_ADDR1     = 0x005E
REG_DDS_CYC1       = 0x005F
REG_CFG_ERROR      = 0x0060
SRAM_ADDRESS_MIN   = 0x6000
SRAM_ADDRESS_MAX   = 0x6FFF

UPDATE_SETTINGS    = 0x01
MEM_ACCESS_ENABLE  = 0x04
MEM_ACCESS_DISABLE = 0x00
START_PATTERN      = 0x01
STOP_PATTERN       = 0x00

SPI_READ_MASK      = 0x80
SPI_WRITE_MASK     = 0x7F

BUF_READ           = 0x08
MASTER_CLOCK       = 125000000
FREQ_RESOLUTION    = 0x1000000

GAIN_MAX           = 2.0
GAIN_MIN           = -2.0
GAIN_RESOLUTION    = 1024
DEFAULT_GAIN       = 0.5
DEFAULT_FREQUENCY  = 100000

WAVE_SINE              = 0x00
WAVE_COSINE            = 0x01
WAVE_TRIANGLE          = 0x02
WAVE_POSITIVE_SAWTOOTH = 0x03
WAVE_NEGATIVE_SAWTOOTH = 0x04

WAV_CFG_PRESTORE_CST         = 0x00
WAV_CFG_PRESTORE_SAWTOOTH    = 0x10
WAV_CFG_PRESTORE_PSEUDO      = 0x20
WAV_CFG_PRESTORE_DDS         = 0x30
WAV_CFG_WAVE_FROM_RAM        = 0x00
WAV_CFG_WAVE_PRESTORED       = 0x01
WAV_CFG_WAVE_PRESTORED_DELAY = 0x02
WAV_CFG_WAVE_PRESTORED_RAM   = 0x03
DDSX_CFG_ENABLE_COSINE       = 0x08
SAW_CFG_RAMP_UP              = 0x00
SAW_CFG_RAMP_DOWN            = 0x01
SAW_CFG_TRIANGLE             = 0x02
SAW_CFG_NO_WAVE              = 0x03
SAW_CFG_STEP_1               = 0x04

def usleep(x:int):
    time.sleep(x/1000000.0)

def bit_not(n, numbits=8):
    return (1 << numbits) - 1 - n

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
    out(pins, 2) # v = OSR >> 2
    label("length_loop")
    jmp(y_dec, "length_loop")
    jmp(x_dec, "two_pulses")

    # pull the next config
    pull(block)

    # get the pulse length and pulse voltage and set the corresponding outputs
    set(x, 2)
    label("two_pulses2")
    out(y, 14) # t = OSR >> 14
    out(pins, 2) # v = OSR >> 2
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

class AD910X():
    def __init__(self):
        self.pin_cs = Pin(PS_SPI_CS, mode=Pin.OUT, value=1)
        self.pin_reset = Pin(PS_RESET, mode=Pin.OUT, value=1)
        self.pin_trigger = Pin(PS_TRIGGER, mode=Pin.OUT, value=1)
        self.spi = SPI(0,
                  baudrate=100000,
                  polarity=1,
                  phase=1,
                  bits=8,
                  firstbit=SPI.MSB,
                  sck=Pin(PS_SPI_SCK),
                  mosi=Pin(PS_SPI_MOSI),
                  miso=Pin(PS_SPI_MISO))

    def spi_write_registers(self, addr:int, data:list[int]):
        """
        Write a list of 16-bit data to AD910x SPI/SRAM register

        Parameters:
            addr: 16-bit SPI/SRAM start address
            data: list of 16-bit data to be written
        """
        tx_buf = [0] * 259
        tx_buf[0] = ((((addr >> 8) & 0xFF) & SPI_WRITE_MASK) & 0xFF)
        tx_buf[1] = (addr & 0xFF)
        for cnt in range(len(data)):
            tx_buf[( cnt * 2 ) + 2] = ((data[cnt] >> 8) & 0xFF)
            tx_buf[( cnt * 2 ) + 3] = (data[cnt] & 0xFF)
        self.pin_cs.value(0)
        self.spi.write(bytes(tx_buf))
        self.pin_cs.value(1)
        usleep(1)

    def spi_read_registers(self, addr:int, length:int) -> list[int]:
        """
        Read a list of 16-bit data from AD910x SPI/SRAM register.

        Parameters:
            addr: 16-bit SPI/SRAM start address.
            length: number of registers to read.

        Returns:
            16-bit data returned by AD910x
        """
        tx_buf = [0] * 2
        tx_buf[0] = (((( addr >> 8 ) & 0xFF ) | SPI_READ_MASK) & 0xFF)
        tx_buf[1] = (addr & 0xFF )
        self.pin_cs.value(0)
        self.spi.write(bytes(tx_buf))
        rx_buf = list(self.spi.read(length * 2))
        self.pin_cs.value(1)
        if len(rx_buf) == 0:
            return []
        data_out = [0] * length
        for cnt in range(0, length):
            data_out[cnt] = (rx_buf[cnt * 2] << 8) | rx_buf[(cnt * 2) + 1]
        usleep(1)
        return data_out

    def spi_write_register(self, addr:int, data:int):
        """
        Write 16-bit data to AD910x SPI/SRAM register

        Parameters:
            addr: 16-bit SPI/SRAM address
            data: 16-bit data to be written to register address
        """
        self.spi_write_registers(addr, [data])

    def spi_read_register(self, addr:int) -> int:
        """
        Read 16-bit data from AD910x SPI/SRAM register.

        Parameters:
            addr: 16-bit SPI/SRAM address.

        Returns:
            16-bit data returned by AD910x.
        """
        data = self.spi_read_registers(addr, 1)
        if len(data) > 0:
            return data[0]
        return 0x00

    def reset(self):
        """
        Reset AD910x SPI registers to default values
        """
        self.pin_reset.low()
        usleep(10)
        self.pin_reset.high()

    def print_data(addr:int, data:int):
        """
        Print register address and data in hexadecimal format

        Parameters:
            addr: 16-bit SPI/SRAM register address
            data: 16-bit data
        """
        print(f'0x{addr:0>4X}, 0x{data:0>4X}')

    def write_sram(self, addr:int, data:list[int]):
        """
        Write data to SRAM.

        Parameters:
            addr: 16-bit SPI/SRAM register start address.
            data: array of 16-bit data to be written to SRAM.
        """
        if (addr < SRAM_ADDRESS_MIN) or (addr > SRAM_ADDRESS_MAX) or (( addr + len(data)) > (SRAM_ADDRESS_MAX + 1)):
            raise Exception("SRAM address not in range [0x6000, 0x6FFF]")
        self.spi_write_register(REG_PAT_STATUS, MEM_ACCESS_ENABLE)
        for cnt in range(0, len(data)):
            self.spi_write_register(addr + cnt, data[cnt] << 4)
        self.spi_write_register(REG_PAT_STATUS, MEM_ACCESS_DISABLE)

    def read_sram(self, addr:int, length:int) -> list[int]:
        """
        Read array of 16-bit data from SRAM.

        Parameters:
            length: number of SRAM addresses to be read from.

        Returns:
            Array of 16-bit data read from SRAM.
        """
        if (addr < SRAM_ADDRESS_MIN) or (addr > SRAM_ADDRESS_MAX) or ((addr + length) > (SRAM_ADDRESS_MAX + 1)):
            raise Exception("SRAM address not in range [0x6000, 0x6FFF]")
        self.spi_write_register(REG_PAT_STATUS, MEM_ACCESS_ENABLE | BUF_READ)
        data = [0] * length
        for cnt in range(0, length):
            data[cnt] = self.spi_read_register(addr + cnt) >> 4
        self.spi_write_register(REG_PAT_STATUS, MEM_ACCESS_DISABLE)
        return data

    def print_sram(self, n:int):
        """
        Read from SRAM and print data.

        Parameters:
            n: number of SRAM addresses to be read from
        """
        self.spi_write_register(REG_PAT_STATUS, 0x000C)
        sram_add = 0x6000
        for i in range(0, n):
            data_shifted = self.spi_read(sram_add + i) >> 2
            self.print_data(sram_add + i, data_shifted)
        self.spi_write_register(REG_PAT_STATUS, 0x0010)

    def update_regs(self, data:list[int]):
        """
        Write to SPI registers, and read and print new register values.

        Parameters:
            data: array of data to written to SPI registers
        """
        data_display = 0
        for i in range(0, 66):
            self.spi_write_register(self.reg_add[i], data[i])
            data_display = self.spi_read(self.reg_add[i])
            self.print_data(self.reg_add[i], data_display)

    def start_pattern(self):
        """
        Start pattern generation by setting AD910x trigger pin to 0.
        """
        self.spi_write_register(REG_PAT_STATUS, START_PATTERN)
        self.pin_trigger.low()

    def stop_pattern(self):
        """
        Stop pattern generation by setting AD910x trigger pin to 1.
        """
        self.spi_write_register(REG_PAT_STATUS, STOP_PATTERN)
        self.pin_trigger.high()

    def update_settings(self):
        """
        Update the settings of AD910x.
        """
        self.spi_write_register(REG_RAM_UPDATE, UPDATE_SETTINGS)

    def set_frequency(self, freq:int):
        """
        Set the frequency of the waveform.

        Parameters:
            freq: Frequency to be set.
        """
        if freq > MASTER_CLOCK:
            raise Exception("Frequency not supported.")
        freq_tmp = int((freq / (MASTER_CLOCK / FREQ_RESOLUTION))) & 0xFFFFFFFF
        tw_msb = ((freq_tmp >> 8) & 0xFFFF)
        tw_lsb = ((freq_tmp << 8 ) & 0xFF00)
        self.stop_pattern()
        self.spi_write_register(REG_DDS_TW32, tw_msb)
        self.spi_write_register(REG_DDS_TW1, tw_lsb)
        self.update_settings()
        self.start_pattern()

    def set_gain(self, gain:float):
        """
        Set the gain of the DAC.

        Parameters:
            gain: Gain to be set.
        """
        if gain > GAIN_MAX or gain < GAIN_MIN:
            raise Exception("Gain value not supported.")
        gain_tmp = (int((gain * GAIN_RESOLUTION)) << 4) & 0xFFFFFFFF
        self.stop_pattern()
        self.spi_write_register(REG_DAC1_DGAIN, gain_tmp)
        self.update_settings()
        self.start_pattern()

    def set_wave_output(self, wave:int):
        """
        Set the type of wave to output.

        Parameters:
            wave: Waveform identifier.
        """
        if wave < WAVE_SINE or wave > WAVE_NEGATIVE_SAWTOOTH:
            raise Exception("Waveform identifier not supported.")
        reg_address = REG_WAV21_CONFIG
        self.stop_pattern()
        reg_data = self.spi_read_register(reg_address) & 0xFF00

        if wave < WAVE_TRIANGLE:
            reg_data |= (WAV_CFG_PRESTORE_DDS | WAV_CFG_WAVE_PRESTORED)
            self.spi_write_register(reg_address, reg_data)
            reg_data = self.spi_read_register(REG_DDSX_CONFIG)
            if wave == WAVE_COSINE:
                reg_data |= DDSX_CFG_ENABLE_COSINE
            else:
                reg_data &= bit_not((DDSX_CFG_ENABLE_COSINE & 0xFFFF))
            self.spi_write_register(REG_DDSX_CONFIG, reg_data)
        else:
            reg_data |= ((WAV_CFG_PRESTORE_SAWTOOTH | WAV_CFG_WAVE_PRESTORED))
            self.spiw_write_register(reg_address, reg_data)
            reg_address = REG_SAW21_CONFIG
            reg_data = self.spi_read_register(reg_address) & 0xFF00

            if wave == WAVE_TRIANGLE:
                reg_data |= ((SAW_CFG_TRIANGLE | SAW_CFG_STEP_1))
            elif wave == WAVE_POSITIVE_SAWTOOTH:
                reg_data |= ((SAW_CFG_RAMP_UP | SAW_CFG_STEP_1))
            else:
                reg_data |= ((SAW_CFG_RAMP_DOWN | SAW_CFG_STEP_1))
            self.spi_write_register(reg_address, reg_data)
        self.update_settings()
        self.start_pattern()

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
        set_multiplexing: Enables the multiplexing mode of the PicoGlitcher version 2 to switch between different voltage levels.
        set_dead_zone: Set a dead time that prohibits triggering within a certain time (trigger rejection). This is intended to exclude false trigger conditions. Can also be set to 0 to disable this feature.
        arm: Arm the PicoGlitcher and wait for the trigger condition. The trigger condition can either be when the reset on the target is released or when a certain pattern is observed in the serial communication. 
        arm_multiplexing: 
        block: Block until trigger condition is met. Raises an exception if times out.
        change_config_and_reset: Change the content of the configuration file `config.json`. Can for example be used to change the initial voltage for multiplexing.
    """
    def __init__(self):
        """
        Default constructor.
        Initializes the PicoGlitcher with the default configuration.
        - Disables `VTARGET`
        - Enables the low-power MOSFET for glitching
        - Configures the PicoGlitcher to use the rising-edge triggger condition.
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
        # pins for multiplexing (only hardware version 2)
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
        # standard dead zone after power down
        self.dead_time = 0.0
        self.pin_condition = self.pin_vtarget_en
        self.condition = 0
        # Pulse shaping expansion board related stuff
        self.ad910x = AD910X()

    def test_waveform_generator(self):
        self.ad910x.set_frequency(DEFAULT_FREQUENCY)
        self.ad910x.set_gain(DEFAULT_GAIN)
        self.ad910x.set_wave_output(WAVE_COSINE)

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
            self.trigger_inverting = False
        elif pin_trigger == "alt":
            self.pin_trigger = Pin(ALT_TRIGGER, Pin.IN, Pin.PULL_DOWN)
            self.trigger_inverting = False
        elif pin_trigger == "ext1":
            self.pin_trigger = Pin(EXT1, Pin.IN, Pin.PULL_DOWN)
            self.trigger_inverting = True
        elif pin_trigger == "ext2":
            self.pin_trigger = Pin(EXT2, Pin.IN, Pin.PULL_DOWN)
            self.trigger_inverting = True

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

    def set_multiplexing(self, vinit="1.8"):
        """
        Enables the multiplexing mode of the PicoGlitcher version 2 to switch between different voltage levels.
        """
        if self.config["hardware_version"][0] < 2:
            raise Exception("Multiplexing not implemented in hardware version 1.")
        self.glitch_mode = "mul"
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

    def arm_common(self):
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
            if self.condition == 1:
                sm2_func = block_rising_condition
            else:
                sm2_func = block_falling_condition
            self.sm2 = StateMachine(2, sm2_func, freq=self.frequency, in_base=self.pin_condition)
            # push dead time (in seconds) into the fifo of the statemachine
            self.sm2.put(int(self.dead_time * self.frequency))

        elif self.trigger_mode == "uart":
            # state machine that checks the trigger condition
            self.sm1 = StateMachine(1, uart_trigger, freq=self.baudrate * 8, in_base=self.pin_trigger)
            # push pattern into the fifo of the statemachine
            pattern = self.pattern << (32 - self.number_of_bits)
            self.sm1.put(pattern)
            # push number of bits into the fifo of the statemachine (self.number_of_bits - 1 is an optimization here)
            self.sm1.put(self.number_of_bits - 1)

        if self.sm0 is not None:
            self.sm0.active(1)
        if self.sm1 is not None:
            self.sm1.active(1)
        if self.sm2 is not None:
            self.sm2.active(1)

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

        # state machine that emits the glitch if the trigger condition is met
        self.sm0 = StateMachine(0, glitch, freq=self.frequency, set_base=self.pin_glitch, sideset_base=self.pin_glitch_en)
        # push delay and length (in nano seconds) into the fifo of the statemachine
        self.sm0.put(delay // (1_000_000_000 // self.frequency))
        self.sm0.put(length // (1_000_000_000 // self.frequency))

        self.arm_common()

    def arm_multiplexing(self, delay:int, mul_config:dict):
        """
        Arm the PicoGlitcher in multiplexing mode and wait for the trigger condition. The trigger condition can either be when the reset on the target is released or when a certain pattern is observed in the serial communication.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            mul_config: The dictionary for the multiplexing profile with pairs of identifiers and values. For example, this could be `{"t1": 10, "v1": "GND", "t2": 20, "v2": "1.8", "t3": 30, "v3": "GND", "t4": 40, "v4": "1.8"}`. Meaning that when triggered, a GND-voltage pulse with duration of `10ns` is emitted, followed by a +1.8V step with duration of `20ns` and so on. Note: The default voltage when performing fault injection in multiplexing mode is 3.3V. This can not be changed by the variable `mul_config`. If you need to have a different default voltage, you may need to modify the `multiplex()` PIO-function.
        """
        if self.config["hardware_version"][0] < 2:
            raise Exception("Multiplexing not implemented in hardware version 1.")

        self.pin_mux1.value(MUX1_INIT)
        self.pin_mux0.value(MUX0_INIT)

        # state machine that emits the glitch if the trigger condition is met (part 1)
        self.sm0 = StateMachine(0, multiplex, freq=self.frequency, set_base=self.pin_glitch, out_base=self.pin_glitch, sideset_base=self.pin_glitch_en)
        # push multiplexing shape config into the fifo of the statemachine
        self.sm0.put(delay // (1_000_000_000 // self.frequency))
        try:
            t1 = mul_config["t1"] // (1_000_000_000 // self.frequency)
            v1 = self.voltage_map[mul_config["v1"]]
        except Exception as _:
            t1 = 0
            v1 = 0b00
        try:
            t2 = mul_config["t2"] // (1_000_000_000 // self.frequency)
            v2 = self.voltage_map[mul_config["v2"]]
        except Exception as _:
            t2 = 0
            v2 = 0b00
        config = v2 << 30 | t2 << 16 | v1 << 14 | t1
        self.sm0.put(config)
        # push the next multiplexing shape config into the fifo of the statemachine
        try:
            t3 = mul_config["t3"] // (1_000_000_000 // self.frequency)
            v3 = self.voltage_map[mul_config["v3"]]
        except Exception as _:
            t3 = 0
            v3 = 0b00
        try:
            t4 = mul_config["t4"] // (1_000_000_000 // self.frequency)
            v4 = self.voltage_map[mul_config["v4"]]
        except Exception as _:
            t4 = 0
            v4 = 0b00
        config = v4 << 30 | t4 << 16 | v3 << 14 | t3
        self.sm0.put(config)

        self.arm_common()

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
                raise Exception("Function execution timed out!")

    def get_sm1_output(self):
        if self.sm1 is not None:
            # pull the output of statemachine 2
            res = self.sm1.get()
            print(res)

    def change_config_and_reset(self, key, value):
        """
        Change the content of the configuration file `config.json`. Note that the value to be changed must already exist.

        Parameters:
            key: Key of value to be replacedl.
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

        machine.soft_reset()
        #machine.reset()