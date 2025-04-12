# Changelog

This is a brief summary of the different versions of Pico Glitcher and what has changed between versions.

## Pico Glitcher v1

### v1.0

- First prototype version of the Pico Glitcher with mainly the Raspberry Pi Pico, two power MOSFETs for glitching, level shifters and a switchable power supply.

### v1.1

- Public release of the Pico Glitcher v1.1
- Layouting changed. Fixed issues with some LEDs not lighting correctly.

## Pico Glitcher v2

### v2.0

- First prototype version of the Pico Glitcher v2.
- v2.0 included for the first time a voltage multiplexer that could switch between GND, 1.8V, 3.3V and an arbitrary voltage applied to the VIN input.
- Because a logic gate with open drain outputs was selected, the multiplexer stage did not work properly. This could be fixed with additional pull-up resistors.
- The capacity of the capacitor on the VTARGET output was reduced.

### v2.1

- Public release of the Pico Glitcher v2.1.
- The logic gates were fixed and the multiplexer stage works correctly.
- Increased the pin count of the multi-purpose GPIO header from 16 pins to 20 pins to support the pulse shaping expansion board.
- Removed the level shifters between GPIO pins 16-19 to interface the pulse shaping expansion board.

### v2.2

- Improved PCB layout, such as thicker tracks for power traces.
- In order to switch between two arbitrary voltages with the multiplexer stage, the connection to 3.3V has been removed. Instead, a second input (VIN2) on the multiplexer stage can be used to supply a second arbitrary voltage.
- The multiplexer stage now consists of two arbitrary voltage inputs (VIN1, VIN2) and a second jumper to fix VIN2 at 3.3V.

### v2.3

- Replaced the TPS2041 power switch with the TPS22860 power switch, which has a faster switching rate and can switch lower voltages.
- Replaced NH245 level shifters with TXB0108 bi-directional level shifters.
- Removed the capacitors on the VTARGET output. This allows for faster switch on and off the power ouput.
- Major problems with this version: The red power LED did not light properly. Also, the level shifters did not work properly because they did not sense the signal direction correctly. This meant that the Pico Glitcher v2.3 could only be used with 3.3V logic levels. All other functions remain unaffected.

### v2.4

- Improved PCB layout.
- Switched back to NH245 level shifters which proved to be the better choice for that application.
- Added a 10Ω resistor to the VTARGET output to protect the power switch. This 10Ω resistor can be bypassed by shorting the solder bridge below the resistor.
