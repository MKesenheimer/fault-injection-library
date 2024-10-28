# Customize your Pico Glitcher

In some cases the functionality findus provide will not be sufficient and you have to write your own code. 

## GPIO pin overview

The Pico Glitcher is built from these components:

![Pico Glitcher v1.1 components](images/pico-glitcher-v1.1-components.png)

The GPIO pins of the Raspberry Pi Pico are connected to the following outlets:

| GPIO Pin | Function                                                |
|----------|---------------------------------------------------------|
| 0        | Reset (with level shifter)                              |
| 1        | Glitch_en                                               |
| 2 - 7    | unused outputs (with level shifter)                     |
| 8 - 14   | unused inputs (with level shifter)                      |
| 15       | Trigger (with level shifter)                            |
| 16       | high-power glitch output                                |
| 17       | low-power glitch output                                 |
| 18       | Trigger (without level shifter), currently unused       |
| 19       | Glitch output (without level shifter), currently unused |
| 20       | VTarget enable                                          |
| 21       | VTarget over current input, currently unused            |
| 22       | unused                                                  |
| 26       | Analog input, currently unused                          |
| 27       | unused                                                  |
| 28       | unused                                                  |

## GPIO pin header

If you want to write code for additional communication protocols, such as a UART-to-USB adapter, or an SPI-to-USB adapter, then the unused GPIO pins are perfect for that.
The output pins with level-shifting are `GPIO2` - `GPIO7`. For inputs the pins `GPIO8` - `GPIO14` can be used.

## Modify the MicroPython script

Add your modifications to `mpGlitcher.py` ([https://github.com/MKesenheimer/fault-injection-library/blob/master/findus/mpGlitcher.py](https://github.com/MKesenheimer/fault-injection-library/blob/master/findus/mpGlitcher.py), or `fault-injection-library/findus/mpGlitcher.py` if you cloned the whole repository) and upload the MicroPython script to the Raspberry Pi Pico:

```bash
upload --port /dev/<rpi-tty-port> mpGlitcher.py
```
