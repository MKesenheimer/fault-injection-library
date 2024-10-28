# Welcome to findus (aka Fault-Injection-Library)

This library is intended to make fault injection attacks against microcontrollers accessible for hobbyists and to introduce the topic of voltage glitching.
This software offers an easy entry point to carry out your own attacks against microcontrollers, SoCs and CPUs.
With the provided and easy to use functions and classes, fault injection projects can be realized quickly.

![Pico Glitcher Board](images/pgfpv1.1-1.jpg)

This library is based on [TAoFI-FaultLib](https://github.com/raelize/TAoFI-FaultLib).
However, several new features have been implemented.
For example, the original library was developed to work with the [ChipWhisperer-Husky](https://rtfm.newae.com/Capture/ChipWhisperer-Husky/) only.
This library has been rewritten to work with hardware that consists of a common MOSFET, the [Raspberry Pi Pico](https://www.raspberrypi.com/products/raspberry-pi-pico/) as the controller and a few other cheap components.
The Raspberry Pi Pico is not only cheap and available for the hobbyist, but also a very capable microcontroller.
Furthermore, this library supports the [ChipWhisperer Pro](https://rtfm.newae.com/Capture/ChipWhisperer-Pro/) as well.

The database functionality has been expanded to a certain extent, too.
With this implementation, e.g. one can add experiments to a previous measurement campaign.