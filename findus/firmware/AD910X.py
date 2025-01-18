import time
from machine import Pin, SPI

# pin assignment
PS_TRIGGER = 5
PS_RESET = 6
PS_SPI_MISO = 16
PS_SPI_CS = 17
PS_SPI_SCK = 18
PS_SPI_MOSI = 19

# register addresses
REG_SPI_CONFIG     = 0x0000
REG_POWER_CONFIG   = 0x0001
REG_CLOCK_CONFIG   = 0x0002
REG_REF_ADJ        = 0x0003
REG_DAC_AGAIN      = 0x0007
REG_DACX_RANGE     = 0x0008
REG_DAC_RSET       = 0x000C
REG_CAL_CONFIG     = 0x000D
REG_COMP_OFFSET    = 0x000E
REG_RAM_UPDATE     = 0x001D
REG_PAT_STATUS     = 0x001E
REG_PAT_TYPE       = 0x001F
REG_PATTERN_DLY    = 0x0020
REG_DAC_DOF        = 0x0025
REG_WAV_CONFIG     = 0x0027
REG_PAT_TIMEBASE   = 0x0028
REG_PAT_PERIOD     = 0x0029
REG_DAC_PAT        = 0x002B
REG_DOUT_START_DLY = 0x002C
REG_DOUT_CONFIG    = 0x002D
REG_DAC_CST        = 0x0031
REG_DAC_DGAIN      = 0x0035
REG_SAW_CONFIG     = 0x0037
REG_DDS_TW32       = 0x003E
REG_DDS_TW1        = 0x003F
REG_DDS_PW         = 0x0043
REG_TRIG_TW_SEL    = 0x0044
REG_DDSX_CONFIG    = 0x0045
REG_TW_RAM_CONFIG  = 0x0047
REG_START_DLY      = 0x005C
REG_START_ADDR     = 0x005D
REG_STOP_ADDR      = 0x005E
REG_DDS_CYC        = 0x005F
REG_CFG_ERROR      = 0x0060
SRAM_ADDRESS_MIN   = 0x6000
SRAM_ADDRESS_MAX   = 0x6FFF

# ram update and pat status register macros
UPDATE_SETTINGS    = 0x01
MEM_ACCESS_ENABLE  = 0x04
MEM_ACCESS_DISABLE = 0x00
ENABLE_PATTERN     = 0x02
START_PATTERN      = 0x01
STOP_PATTERN       = 0x00
BUF_READ           = 0x08

# pattern control
PATTERN_RPT_CONTINOUS = 0x00
PATTERN_RPT_FINITE    = 0x01

# SPI read/write setting
SPI_READ_MASK      = 0x80
SPI_WRITE_MASK     = 0x7F

# frequency calculation constants
MASTER_CLOCK       = 125000000
FREQ_RESOLUTION    = 0x1000000

# gain calculation macros
GAIN_MAX           = 2.0
GAIN_MIN           = -2.0
GAIN_RESOLUTION    = 1024
OFFSET_RESOLUTION = 4096
DEFAULT_GAIN       = 0.5
DEFAULT_FREQUENCY  = 100000

# wave output selection macros
WAVE_SINE              = 0x00
WAVE_COSINE            = 0x01
WAVE_TRIANGLE          = 0x02
WAVE_POSITIVE_SAWTOOTH = 0x03
WAVE_NEGATIVE_SAWTOOTH = 0x04

# wave config macros
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

class AD910X():
    def __init__(self):
        self.pin_cs = Pin(PS_SPI_CS, mode=Pin.OUT, value=1)
        self.pin_reset = Pin(PS_RESET, mode=Pin.OUT, value=1)
        self.pin_trigger = Pin(PS_TRIGGER, mode=Pin.OUT, value=1)
        self.spi = SPI(0,
                  baudrate=1000000, # 100000 oder 1000000
                  polarity=0,
                  phase=0,
                  bits=8, # 8 oder 16
                  firstbit=SPI.MSB,
                  sck=Pin(PS_SPI_SCK),
                  mosi=Pin(PS_SPI_MOSI),
                  miso=Pin(PS_SPI_MISO))

    def init(self):
        #self.spi_read_register(REG_SPI_CONFIG)
        # TODO: do a proper calibration!
        #self.spi_write_register(REG_DAC_AGAIN, 0x4000)
        #self.spi_write_register(REG_DAC_RSET, 0x1F00) # DAC_RSET_CAL = 11111
        #self.spi_write_register(REG_DOUT_START_DLY, 0x0003)
        #self.spi_write_register(REG_COMP_OFFSET, ) offset
        pass

    def get_trigger_pin(self):
        """
        TODO
        """
        return self.pin_trigger

    def spi_write_registers(self, addr:int, data:list[int]):
        """
        Write a list of 16-bit data to AD910x SPI/SRAM register

        Parameters:
            addr: 16-bit SPI/SRAM start address
            data: list of 16-bit data to be written
        """
        tx_buf = [0] * (2 * len(data) + 2)
        tx_buf[0] = ((((addr >> 8) & 0xFF) & SPI_WRITE_MASK) & 0xFF)
        tx_buf[1] = (addr & 0xFF)
        for cnt in range(len(data)):
            tx_buf[( cnt * 2 ) + 2] = ((data[cnt] >> 8) & 0xFF)
            tx_buf[( cnt * 2 ) + 3] = (data[cnt] & 0xFF)
        self.pin_cs.value(0)
        self.spi.write(bytes(tx_buf))
        self.pin_cs.value(1)
        #usleep(1)

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
        #usleep(1)
        return data_out

    def spi_write_register_new(self, addr:int, data:int):
        """
        Write 16-bit data to AD910x SPI/SRAM register

        Parameters:
            addr: 16-bit SPI/SRAM address
            data: 16-bit data to be written to register address
        """
        self.pin_cs.value(0)
        addr_bytes = addr.to_bytes(2, 'big')
        self.spi.write(addr_bytes)
        data_bytes = data.to_bytes(2, 'big')
        self.spi.write(data_bytes)
        self.pin_cs.value(1)
        usleep(1)

    def spi_read_register_new(self, addr:int) -> int:
        """
        Read 16-bit data from AD910x SPI/SRAM register.

        Parameters:
            addr: 16-bit SPI/SRAM address.

        Returns:
            16-bit data returned by AD910x.
        """
        read_addr = 0x8000 + addr
        self.pin_cs.value(0)
        self.spi.write(read_addr.to_bytes(2, 'big'))
        data = self.spi.read(1)
        self.pin_cs.value(1)
        usleep(1)
        return int.from_bytes(data, 'big')

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
        usleep(100)
        self.pin_reset.high()
        usleep(100000)

    def trigger_high(self):
        """
        Set trigger pin high (disables pattern generation).
        """
        self.pin_trigger.high()

    def trigger_low(self):
        """
        Set trigger pin low (enables pattern generation).
        """
        self.pin_trigger.low()

    def print_data(self, addr:int, data:int, addrname:str = ""):
        """
        Print register address and data in hexadecimal format

        Parameters:
            addr: 16-bit SPI/SRAM register address
            data: 16-bit data
        """
        if addrname == "":
            print(f'0x{addr:0>4X}: 0x{data:0>4X} = 0b{data:0>16b}')
        else:
            print(f'0x{addr:0>4X} ({addrname}):\t0x{data:0>4X} = 0b{data:0>16b}')

    def write_sram(self, addr:int, data:list[int]):
        """
        Write data to SRAM.

        Parameters:
            addr: 16-bit SPI/SRAM register start address.
            data: array of 16-bit data to be written to SRAM.
        """
        if (addr < SRAM_ADDRESS_MIN) or (addr > SRAM_ADDRESS_MAX) or ((addr + len(data)) > (SRAM_ADDRESS_MAX + 1)):
            raise Exception("SRAM address not in range [0x6000, 0x6FFF]")
        self.spi_write_register(REG_PAT_STATUS, MEM_ACCESS_ENABLE)
        for cnt in range(0, len(data)):
            if data[cnt] > 8190:
                data[cnt] = 8190
            elif data[cnt] < -8190:
                data[cnt] = -8190
            self.spi_write_register(addr + cnt, data[cnt] << 2)
        self.spi_write_register(REG_PAT_STATUS, MEM_ACCESS_DISABLE)

    def write_sram_from_start(self, data:list[int]):
        """
        Write data to SRAM from start address.

        Parameters:
            data: array of 16-bit data to be written to SRAM.
        """
        if len(data) > 4096:
            raise Exception("SRAM data too large.")
        self.write_sram(SRAM_ADDRESS_MIN, data)

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
            data[cnt] = self.spi_read_register(addr + cnt) >> 2
        self.spi_write_register(REG_PAT_STATUS, MEM_ACCESS_DISABLE)
        return data

    def print_sram(self, length:int):
        """
        Read from SRAM and print data.

        Parameters:
            n: number of SRAM addresses to be read from
        """
        data = self.read_sram(SRAM_ADDRESS_MIN, length)
        for i in range(len(data)):
            self.print_data(SRAM_ADDRESS_MIN + i, data[i])

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
        self.spi_write_register(REG_DDS_TW32, tw_msb)
        self.spi_write_register(REG_DDS_TW1, tw_lsb)

    def set_gain(self, gain:float):
        """
        Set the gain of the DAC.

        Parameters:
            gain: Gain to be set.
        """
        if gain > GAIN_MAX or gain < GAIN_MIN:
            raise Exception("Gain value not supported.")
        gain_tmp = (int((gain * GAIN_RESOLUTION)) << 4) & 0xFFFF
        self.spi_write_register(REG_DAC_DGAIN, gain_tmp)

    def set_offset(self, offset:int):
        """
        Set the offset of the DAC.

        Parameters:
            offset: Offset to be set.
        """
        if offset < 0 or offset > 4096:
            raise Exception("Offset value not supported.")
        self.spi_write_register(REG_DAC_DOF, offset)

    def update_sram(self, pulse_number_of_points:int):
        self.spi_write_register(REG_START_ADDR, 0x0000) # start SRAM addr to read data from
        stop_addr = (((pulse_number_of_points & 0x0FFF) - 1) << 4) & 0xFFF0
        self.spi_write_register(REG_STOP_ADDR, stop_addr)  # stop SRAM addr
        self.spi_write_register(REG_RAM_UPDATE, UPDATE_SETTINGS)
        self.spi_write_register(REG_PAT_STATUS, START_PATTERN)

    def set_pulse_output_oneshot(self):
        """
        Configure the DDS to output one defined pulse.

        Parameters:
            pulse: The pulse to output
        """
        # update settings
        self.spi_write_register(REG_PAT_TYPE, PATTERN_RPT_FINITE) # pattern is emitted a finite amount of times
        self.spi_write_register(REG_DAC_PAT, 0x0001) # repeat pattern once
        self.spi_write_register(REG_WAV_CONFIG, WAV_CFG_PRESTORE_DDS) # output from DDS
        self.spi_write_register(REG_PAT_TIMEBASE, 0x0111) # HOLD = 1, PAT_PERIOD_BASE = 1, START_DELAY_BASE = 1; TODO: set the time base, TODO: HOLD = 0 for faster sampling?
        #self.spi_write_register(REG_PATTERN_DLY, 0x000E) # TODO: control this by the delay parameter
        #self.spi_write_register(REG_START_DLY, 0x0003) # TODO: OR: control this by the delay parameter

    def set_wave_output(self, wave:int):
        """
        Set the type of wave to output.

        Parameters:
            wave: Waveform identifier.
        """
        if wave < WAVE_SINE or wave > WAVE_NEGATIVE_SAWTOOTH:
            raise Exception("Waveform identifier not supported.")
        reg_address = REG_WAV_CONFIG
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
            self.spi_write_register(reg_address, reg_data)
            reg_address = REG_SAW_CONFIG
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
        return self.spi_read_register(REG_CFG_ERROR)

    def update_regs(self, data):
        regadd = [0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x0008, 0x0009, 0x000a, 0x000b, 0x000c, 0x000d, 0x000e, 0x001f, 0x0020, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027, 0x0028, 0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f, 0x0030, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037, 0x003e, 0x003f, 0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0047, 0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057, 0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f, 0x001e, 0x001d]
        for i in range(len(regadd)):
            self.spi_write_register(regadd[i], data[i])

    def set_pulse_output_test(self):
        #self.stop_pattern()
        regval = [0x0000, 0x0e00, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x4000, 0x0000, 0x0000, 0x0000, 0x0000, 0x1f00, 0x0000, 0x0000, 0x0001, 0x000E, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x3030, 0x0111, 0xffff, 0x0000, 0x0101, 0x0003, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x4000, 0x0000, 0x0200, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0x0fa0, 0x0000, 0xfff0, 0x0100, 0x0001, 0x0001]
        self.update_regs(regval)

    def debug_registers(self):
        self.print_data(REG_WAV_CONFIG, self.spi_read_register(REG_WAV_CONFIG), "REG_WAV_CONFIG")
        self.print_data(REG_DDSX_CONFIG, self.spi_read_register(REG_DDSX_CONFIG), "REG_DDSX_CONFIG")
        self.print_data(REG_DAC_DGAIN, self.spi_read_register(REG_DAC_DGAIN), "REG_DAC_DGAIN")
        self.print_data(REG_DDS_TW32, self.spi_read_register(REG_DDS_TW32), "REG_DDS_TW32")
        self.print_data(REG_DDS_TW1, self.spi_read_register(REG_DDS_TW1), "REG_DDS_TW1")
        self.print_data(REG_DOUT_START_DLY, self.spi_read_register(REG_DOUT_START_DLY), "REG_DOUT_START_DLY")
        self.print_data(REG_PATTERN_DLY, self.spi_read_register(REG_PATTERN_DLY), "REG_PATTERN_DLY")
        self.print_data(REG_PAT_STATUS, self.spi_read_register(REG_PAT_STATUS), "REG_PAT_STATUS")
        self.print_data(REG_RAM_UPDATE, self.spi_read_register(REG_RAM_UPDATE), "REG_RAM_UPDATE")
        self.print_data(REG_CFG_ERROR, self.spi_read_register(REG_CFG_ERROR), "REG_CFG_ERROR")
        print()

    def set_wave_output_test(self):
        self.pin_trigger.high()

        gain = 0.5
        gain_tmp = (int((gain * GAIN_RESOLUTION)) << 4) & 0xFFFFFFFF
        self.spi_write_register(REG_DAC_DGAIN, gain_tmp)

        freq = 1000000
        freq_tmp = int((freq / (MASTER_CLOCK / FREQ_RESOLUTION))) & 0xFFFFFFFF
        tw_msb = ((freq_tmp >> 8) & 0xFFFF)
        tw_lsb = ((freq_tmp << 8 ) & 0xFF00)
        self.spi_write_register(REG_DDS_TW32, tw_msb)
        self.spi_write_register(REG_DDS_TW1, tw_lsb)

        reg_data = self.spi_read_register(REG_WAV_CONFIG) & 0xFF00
        reg_data |= (WAV_CFG_PRESTORE_DDS | WAV_CFG_WAVE_PRESTORED) # debug: 0x31 = 0b110001
        self.spi_write_register(REG_WAV_CONFIG, reg_data)

        reg_data = self.spi_read_register(REG_DDSX_CONFIG)
        reg_data |= DDSX_CFG_ENABLE_COSINE
        self.spi_write_register(REG_DDSX_CONFIG, reg_data) # debug: 0x08

        self.spi_write_register(REG_RAM_UPDATE, 0x0001)
        self.spi_write_register(REG_PAT_STATUS, 0x0001)
        self.debug_registers()
        self.pin_trigger.low()

        return self.spi_read_register(REG_CFG_ERROR)