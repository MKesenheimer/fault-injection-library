import ujson
from rp2 import PIO

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
    # added as dummy variables to fix undefined variable error
    MUX0_PIO_INIT = None
    MUX1_PIO_INIT = None
    MUX_PIO_INIT = 0b00
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
    elif config["mux_vinit"] == "VI1" or config["mux_vinit"] == "VCC":
        MUX1_INIT = 0
        MUX0_INIT = 0
        MUX1_PIO_INIT = PIO.OUT_LOW
        MUX0_PIO_INIT = PIO.OUT_LOW
        MUX_PIO_INIT = 0b00
    elif config["mux_vinit"] == "1.8":
        MUX1_INIT = 1
        MUX0_INIT = 0
        MUX1_PIO_INIT = PIO.OUT_HIGH
        MUX0_PIO_INIT = PIO.OUT_LOW
        MUX_PIO_INIT = 0b01
    else: # 3.3 or VI2
        MUX1_INIT = 0
        MUX0_INIT = 1
        MUX1_PIO_INIT = PIO.OUT_LOW
        MUX0_PIO_INIT = PIO.OUT_HIGH
        MUX_PIO_INIT = 0b10