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

# example pulseforms
GAUSSIAN_PULSE = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 15, 15, 15, 16, 16, 16, 17, 17, 17, 18, 18, 18, 19, 19, 20, 20, 20, 21, 21, 22, 22, 23, 23, 23, 24, 24, 25, 25, 26, 27, 27, 28, 28, 29, 29, 30, 31, 31, 32, 33, 33, 34, 35, 35, 36, 37, 37, 38, 39, 40, 41, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60, 61, 62, 63, 65, 66, 67, 69, 70, 72, 73, 75, 76, 78, 79, 81, 82, 84, 86, 88, 89, 91, 93, 95, 97, 99, 101, 103, 105, 107, 109, 111, 114, 116, 118, 121, 123, 126, 128, 131, 133, 136, 139, 142, 145, 148, 151, 154, 157, 160, 163, 166, 170, 173, 177, 180, 184, 188, 192, 195, 199, 203, 207, 212, 216, 220, 225, 229, 234, 239, 244, 249, 254, 259, 264, 269, 275, 280, 286, 292, 298, 304, 310, 316, 322, 329, 336, 342, 349, 356, 364, 371, 378, 386, 394, 402, 410, 418, 427, 435, 444, 453, 462, 472, 481, 491, 501, 511, 521, 532, 543, 554, 565, 576, 588, 600, 612, 624, 637, 650, 663, 676, 690, 704, 718, 733, 748, 763, 778, 794, 810, 826, 843, 860, 877, 895, 913, 932, 951, 970, 989, 1009, 1030, 1051, 1072, 1093, 1116, 1138, 1161, 1185, 1208, 1233, 1258, 1283, 1309, 1336, 1363, 1390, 1418, 1447, 1476, 1506, 1536, 1567, 1599, 1631, 1664, 1698, 1732, 1767, 1803, 1840, 1877, 1915, 1953, 1993, 2033, 2074, 2116, 2159, 2202, 2247, 2292, 2339, 2386, 2434, 2483, 2533, 2585, 2637, 2690, 2744, 2800, 2856, 2914, 2973, 3033, 3094, 3157, 3221, 3286, 3352, 3420, 3489, 3560, 3631, 3705, 3780, 3856, 3934, 4013, 4095, 4013, 3934, 3856, 3780, 3705, 3631, 3560, 3489, 3420, 3352, 3286, 3221, 3157, 3094, 3033, 2973, 2914, 2856, 2800, 2744, 2690, 2637, 2585, 2533, 2483, 2434, 2386, 2339, 2292, 2247, 2202, 2159, 2116, 2074, 2033, 1993, 1953, 1915, 1877, 1840, 1803, 1767, 1732, 1698, 1664, 1631, 1599, 1567, 1536, 1506, 1476, 1447, 1418, 1390, 1363, 1336, 1309, 1283, 1258, 1233, 1208, 1185, 1161, 1138, 1116, 1093, 1072, 1051, 1030, 1009, 989, 970, 951, 932, 913, 895, 877, 860, 843, 826, 810, 794, 778, 763, 748, 733, 718, 704, 690, 676, 663, 650, 637, 624, 612, 600, 588, 576, 565, 554, 543, 532, 521, 511, 501, 491, 481, 472, 462, 453, 444, 435, 427, 418, 410, 402, 394, 386, 378, 371, 364, 356, 349, 342, 336, 329, 322, 316, 310, 304, 298, 292, 286, 280, 275, 269, 264, 259, 254, 249, 244, 239, 234, 229, 225, 220, 216, 212, 207, 203, 199, 195, 192, 188, 184, 180, 177, 173, 170, 166, 163, 160, 157, 154, 151, 148, 145, 142, 139, 136, 133, 131, 128, 126, 123, 121, 118, 116, 114, 111, 109, 107, 105, 103, 101, 99, 97, 95, 93, 91, 89, 88, 86, 84, 82, 81, 79, 78, 76, 75, 73, 72, 70, 69, 67, 66, 65, 63, 62, 61, 60, 58, 57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 41, 40, 39, 38, 37, 37, 36, 35, 35, 34, 33, 33, 32, 31, 31, 30, 29, 29, 28, 28, 27, 27, 26, 25, 25, 24, 24, 23, 23, 23, 22, 22, 21, 21, 20, 20, 20, 19, 19, 18, 18, 18, 17, 17, 17, 16, 16, 16, 15, 15, 15, 14, 14, 14, 13, 13, 13, 13, 12, 12, 12, 12, 11, 11, 11, 11, 10, 10, 10, 10, 10, 9, 9, 9, 9, 9, 9, 8, 8, 8, 8, 8, 7, 7, 7, 7, 7, 7, 7, 6, 6, 6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

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
                  baudrate=100000,
                  polarity=1,
                  phase=1,
                  bits=8,
                  firstbit=SPI.MSB,
                  sck=Pin(PS_SPI_SCK),
                  mosi=Pin(PS_SPI_MOSI),
                  miso=Pin(PS_SPI_MISO))
        # TODO: SPI config kontrollieren
        # TODO: do a proper calibration!
        self.spi_write_register(REG_DAC_AGAIN, 0x4000)
        self.spi_write_register(REG_DAC_RSET, 0x1F00) # DAC_RSET_CAL = 11111

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

    def write_sram_from_start(self, data:list[int]):
        """
        Write data to SRAM from start address.

        Parameters:
            data: array of 16-bit data to be written to SRAM.
        """
        if len(data) > 4095:
            raise Exception("Pulse too large.")
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
            data[cnt] = self.spi_read_register(addr + cnt) >> 4
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
        self.spi_write_register(REG_DAC_DGAIN, gain_tmp)
        self.update_settings()
        self.start_pattern()

    def set_pulse_output_oneshot(self):
        """
        Configure the DDS to output one defined pulse.

        Parameters:
            pulse: The pulse to output
        """
        # update settings
        self.stop_pattern()
        self.spi_write_register(REG_PAT_TYPE, PATTERN_RPT_FINITE) # pattern is emitted a finite amount of times
        self.spi_write_register(REG_DAC_PAT, 0x0001) # repeat pattern once
        self.spi_write_register(REG_WAV_CONFIG, WAV_CFG_PRESTORE_DDS)
        self.spi_write_register(REG_PAT_TIMEBASE, 0x0111) # HOLD = 1, PAT_PERIOD_BASE = 1, START_DELAY_BASE = 1; TODO: set the time base, TODO: HOLD = 0 for faster sampling?
        self.spi_write_register(REG_PATTERN_DLY, 0x0000) # TODO: control this by the delay parameter
        self.spi_write_register(REG_START_DLY, 0x0000) # TODO: OR: control this by the delay parameter
        self.spi_write_register(REG_START_ADDR, 0x0000) # start SRAM addr to read data from
        self.spi_write_register(REG_STOP_ADDR, 0xFFF0)  # stop SRAM addr
        #self.spi_write_register(REG_DDS_CYC, 0x0100) # ?
        self.spi_write_register(REG_PAT_STATUS, START_PATTERN)
        self.spi_write_register(REG_RAM_UPDATE, UPDATE_SETTINGS)

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
            self.spiw_write_register(reg_address, reg_data)
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
