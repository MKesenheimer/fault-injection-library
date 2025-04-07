# Trezor One v1.6.0 glitching

This short summary will explain how to attack the Trezor One and how to get from RDP level 2 to RDP level 1 with access to RAM. With RAM access, other attacks can be performed, for example another voltage glitching attack to downgrade from RDP-1 to RDP-0.

![](images/01-original-target.JPG)

## Preparations

Begin by covering delicate components with a metal foil and desolder the marked capacitors:

![](images/02-covering-delicate-components.JPG)
![](images/03-desoldered-capacitors.JPG)

Solder a breakout pinheader to the Trezor One to get SWD access:

![](images/04-soldered-breakout-pinheader.JPG)

Glue a SMA connector to the backside of the device and connect the positive lead (middle pin) to the `V_CAP` line and the negative lead to `GND`:

![](images/05-backside.JPG)
![](images/06-sma-connector-on-vcap.JPG)

Connect a ST-Link debug adapter to the SWD lines, and the reset line to `RESET`, as well as the power lines to the Pico Glitcher:

| Trezor pins   | ST-Link | Pico Glitcher |
|---------------|---------|---------------|
| RESET         |         | RESET output  |
| GND           | GND     | GND           |
| SWO           |         |               |
| SWCLK         | SWCLK   |               |
| SWDIO         | SWDIO   |               |
| VDD           | T_VCC   | VTARGET       |
| SMA connector |         | SMA crowbar   |


![](images/07-glitching-setup.JPG)