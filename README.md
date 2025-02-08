# Usage with examples

Findus (aka the fault-injection-library) is a toolchain to perform fault-injection attacks on microcontrollers and other targets.
This library offers an easy entry point to carry out fault-injection attacks against microcontrollers, SoCs and CPUs.
With the provided and easy to use functions and classes, fault-injection projects can be realized quickly with cheap and available hardware.

Findus supports the [ChipWhisperer Pro](https://rtfm.newae.com/Capture/ChipWhisperer-Pro/), the [ChipWhisperer Husky](https://rtfm.newae.com/Capture/ChipWhisperer-Husky/) and the PicoGlitcher.
More information about the ChipWhisperer Pro and the ChipWhisperer Husky can be found on [https://chipwhisperer.readthedocs.io/en/latest/index.html](https://chipwhisperer.readthedocs.io/en/latest/index.html).

## Purchasing the Pico Glitcher

Only a Raspberry Pi Pico and a few other components are required to use this software.
However, in order to achieve the best results, a circuit board was developed that was adapted directly for the fault-injection-library.

The board consists of a Raspberry Pi Pico, two level shifters for in- and outputs with any voltage, and glitching transistors that can switch up to 66 amps.
A multiplexing stage to quickly switch between up to four different voltage levels was added in revision 2.

There are several connection options for different voltage sources, from 1.8V, 3.3V to 5V.
The Pico Glitcher can also be supplied with any external voltage via `VCC_EXTERN`.
To power the target board, it is supplied with power via the `VTARGET` connection.
The output of this voltage source can be controlled via software, i.e. the target can be completely disconnected from power by executing the `power_cycle_target()` command.
This allows a cold start of the target to be carried out in the event of error states that cannot be eliminated by a reset.

![Assembled Pico Glitcher v1](https://github.com/MKesenheimer/fault-injection-library/blob/master/schematics/finished.JPG)

The Pico Glitcher can be purchased from the tindie online store: [https://www.tindie.com/products/faulty-hardware/picoglitcher-v21/](https://www.tindie.com/products/faulty-hardware/picoglitcher-v21/). If you have questions or special requests, please feel free to contact me.

## Documentation

The documentation of the source code and how to use the library and the hardware can be found on [https://fault-injection-library.readthedocs.io/](https://fault-injection-library.readthedocs.io/).

## Cloning

Set up the project by cloning it:

```bash
git clone --depth 1 --recurse-submodules https://github.com/MKesenheimer/fault-injection-library.git
cd fault-injection-lib
```

## Setting up a virtual environment

If you want to make sure that the libraries to be installed do not collide with your local Python environment, use a virtual environment.
Set it up by generating a new virtual environment and by activating it:

```bash
python -m venv .venv
source .venv/bin/activate
```

## Installing

After these steps we have to install `findus` (aka `fault-injection-library`).
Make sure to have pip [installed](https://docs.python.org/3/library/ensurepip.html).

```bash
pip install .
```

If you use the rk6006 power supply and want to power-cycle the target via software, install the rd6006 library (supplied as submodule):

```bash
cd rd6006
pip install .
```

However, usage of the rk6006 power supply is optional.
The Pico Glitcher is also capable of power-cycling the target via software.

## Installing micropython scripts on the Raspberry Pi Pico

Now we have to prepare the Raspberry Pi Pico.
Add the [Micropython firmware](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico).
In general the following script can be used to upload Micropython scripts to the Raspberry Pi Pico.

```bash
upload --port /dev/<rpi-tty-port> --file[s] <file.py> [files...]
```

## Executing Raspberry Pi Pico glitcher example implementation

To carry out a fault injection attack with the Raspberry Pi Pico on another microcontroller, the following setup can be used.

First, we connect the Pico Glitcher and a target as follows:
![Example usage](https://github.com/MKesenheimer/fault-injection-library/blob/master/schematics/fritzing/esp32-glitching.png)
Note that the trigger input is connected directly to the reset line.
As the reset is released from the device, the trigger signal is sent.

We install the corresponding Micropython script and the corresponding config file (must be done only once) on the Raspberry Pi Pico:

```bash
cd findus/firmware
upload --port /dev/<rpi-tty-port> --files FastADC.py PicoGlitcher.py config_v1/config.json
```

For hardware version 2.x of the Pico Glitcher, the corresponding config file must be provided:

```bash
cd findus/firmware
upload --port /dev/tty.<rpi-tty-port> --files AD910X.py FastADC.py PicoGlitcher.py PulseGenerator.py Spline.py config_v2/config.json
```

Although the software is based on Micropython, using the PIO functions of the Raspberry Pi Pico, very precise switching operations can be made and triggered on external signals.

Next, we switch to the directory `example` and execute the script which controls our attack.

```bash
cd example
python pico-glitcher.py --target /dev/tty.<target-tty-port> --rpico /dev/<rpi-tty-port> --delay 1_000 2_000 --length 100 150
```

The script resets the target, arms the pico glitcher, waits for the external trigger (reset high) and emits a glitch of a given length after a certain delay.
The response of the target is then read and classified.
The results are entered into a database, which can be processed in the browser using the command:

```bash
analyzer --directory databases
```

This attack can be used, for example, to bypass the read-out protection (RDP) of Apple Airtags and to download the firmware of these devices.
See [the video by stacksmashing](https://www.youtube.com/watch?v=_E0PWQvW-14) for more details.


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=MKesenheimer/fault-injection-library&type=Date)](https://star-history.com/#MKesenheimer/fault-injection-library&Date)