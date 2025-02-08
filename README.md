# Usage with examples

Findus (aka the fault-injection-library) is a toolchain to perform fault-injection attacks on microcontrollers and other targets.
This library offers an easy entry point to carry out fault-injection attacks against microcontrollers, SoCs and CPUs.
With the provided and easy to use functions and classes, fault-injection projects can be realized quickly with cheap and available hardware.

Findus supports the [ChipWhisperer Pro](https://rtfm.newae.com/Capture/ChipWhisperer-Pro/), the [ChipWhisperer Husky](https://rtfm.newae.com/Capture/ChipWhisperer-Husky/) and the PicoGlitcher.
More information about the ChipWhisperer Pro and the ChipWhisperer Husky can be found on [https://chipwhisperer.readthedocs.io/en/latest/index.html](https://chipwhisperer.readthedocs.io/en/latest/index.html).

## Table of contents

- [Purchasing the Pico Glitcher](#purchasing-the-pico-glitcher)
- [Documentation](#documentation)
- [Installing findus](#installing-findus)
- [Updating the Pico Glitcher firmware](#updating-the-pico-glitcher-firmware)
    - [Step 1: MicroPython firmware](#step-1-microPython-firmware)
    - [Step 2: Install the findus library](#step-2-install-the-findus-library)
    - [Step 3: Upload the Pico Glitcher MicroPython script](#step-3-upload-the-pico-glitcher-micropython-script)
- [Installing from source](#installing-from-source)
- [Test the functionality of your Pico Glitcher](#test-the-functionality-of-your-pico-glitcher)
- [UART Trigger](#uart-trigger)
- [More Examples](#more-examples)
- [Analyzer](#analyzer)
- [Star History](#star-history)

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


## Installing findus

If you just want to get started quickly and don't want to bother with the source code of findus, findus can be installed via pip. The findus library can be found on [https://pypi.org/project/findus/](https://pypi.org/project/findus/) and can be installed locally in a Python environment using the following command:

```bash
mkdir my-fi-project && cd my-fi-project
python -m venv .venv
source .venv/bin/activate
pip install findus
```

Install the optional RD6006 python bindings if you have a RK6006 or a RD6006 power supply from Riden:

```bash
pip install rd6006
```

This external power supply can be used optionally to supply the target with power. It is possible to control the RD6006 power supply via the findus library using the power supply's USB interface. Suitable functions for this are implemented in the findus library.
Don't worry if you don't have this power supply. The Pico Glitcher can also supply the target with voltage.

Now you can use findus:

```bash
python
>>> from findus import Database, PicoGlitcher
...
```

The next step is to copy an existing glitching script and to adapt it to your needs.
Start by copying [https://github.com/MKesenheimer/fault-injection-library/blob/master/example/pico-glitcher.py](https://github.com/MKesenheimer/fault-injection-library/blob/master/example/pico-glitcher.py). More example projects are located at [https://github.com/MKesenheimer/fault-injection-library/tree/master/projects](https://github.com/MKesenheimer/fault-injection-library/tree/master/projects).

See [examples](examples.md) for more information how to use findus and the Pico Glitcher.

## Updating the Pico Glitcher firmware

Your Pico Glitcher should come with the latest firmware already installed. If not, follow the following procedure to update the software on the Pico Glitcher.

### Step 1: MicroPython firmware

Download the MicroPython firmware from [https://micropython.org/download/RPI_PICO/](https://micropython.org/download/RPI_PICO/). Unplug the Pico Glitcher from your computer, press and hold the 'BOOTSEL' button on the Raspberry Pi Pico and connect it back to your computer. The Raspberry Pi Pico should come up as a flash-storage device. Copy the MicroPython firmware ('RPI_PICO-xxxxxxxx-vx.xx.x.uf2') to this drive and wait until the Raspberry Pi Pico disconnects automatically.
More information about setting up the Raspberry Pi Pico can be found [here](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico).

### Step 2: Install the findus library

Skip this step, if you already installed findus previously.

If you want to make sure that the libraries to be installed do not collide with your local Python environment, use a virtual environment.
Set it up by generating a new virtual environment and by activating it:

```bash
python -m venv .venv
source .venv/bin/activate
```

After these steps we have to install findus (aka fault-injection-library).
Make sure to have pip [installed](https://docs.python.org/3/library/ensurepip.html).

```bash
pip install findus
```

### Step 3: Upload the Pico Glitcher MicroPython script

If everything went well, you should have the `upload` script available for execution in your command-line environment.
Connect the Pico Glitcher to your computer and check which serial device comes up:

```bash
ls /dev/tty*
```

Take note of the device path. Next upload the Pico Glitcher firmware and the specific configuration for your Pico Glitcher hardware version (either `config_v1/config.json` or `config_v2/config.json`) via the following command:

```bash
cd .venv/lib/python3.12/site-packages/findus/firmware
upload --port /dev/tty.<rpi-tty-port> --files AD910X.py FastADC.py PicoGlitcher.py \ 
    PulseGenerator.py Spline.py <config-path>/config.json
```

Your Pico Glitcher should now be ready to perform fault-injection attacks.

## Installing from source

If you want to get involved in the development or to have access to all the resources of this repository, clone the findus library:

```bash
git clone --depth 1 --recurse-submodules \ 
    https://github.com/MKesenheimer/fault-injection-library.git
```

Install the findus and the optional rd6006 library:

```bash
cd fault-injection-library
pip install .
cd rd6006
pip install .
```

Then:

```bash
cd findus/firmware
upload --port /dev/tty.<rpi-tty-port> --files AD910X.py FastADC.py PicoGlitcher.py \ 
    PulseGenerator.py Spline.py <config-path>/config.json
```

The next step is to copy an existing glitching script and to adapt it to your needs.
Start by copying `fault-injection-library/example/pico-glitcher.py`. More example projects are located at `fault-injection-library/projects`.


## Test the functionality of your Pico Glitcher

The following  setup can be used to test the Pico Glitcher.

- Connect 'TRIGGER' input with 'RESET'.
- Between 'GLITCH' and 'VTARGET', connect a 10 Ohm resistor (this is the test target in this case).
- Optionally connect channel 1 of an oscilloscope to 'RESET' and channel 2 to 'GLITCH'.

![Example setup](https://github.com/MKesenheimer/fault-injection-library/blob/master/docs/images/test-example.png)

Next, run the test script `pico-glitcher.py` located in `fault-injection-library/example`:

```bash
cd example
python pico-glitcher.py --rpico /dev/<rpi-tty-port> --delay 1000 1000 --length 100 100
```

You should now be able to observe the glitches with an oscilloscope on the 10 Ohm resistor.
Measure the expected delay and glitch length with the oscilloscope.

## UART Trigger

- Connect 'TRIGGER' input to 'RX' and 'TX' of a USB-to-UART adapter
- Between 'GLITCH' and 'VTARGET', connect a 10 Ohm resistor (this is the test target in this case).
- Optionally connect channel 1 of an oscilloscope to 'RESET' and channel 2 to 'GLITCH'.

![Example setup](https://github.com/MKesenheimer/fault-injection-library/blob/master/docs/images/test-example-uart.png)

Next, run the test script `pico-glitcher-uart.py` located in `fault-injection-library/example`:

```bash
cd example
python pico-glitcher-uart.py --rpico /dev/<rpi-tty-port> --target /dev/<target-tty-port> --delay 1000 1000 --length 100 100
```

You should now be able to observe the glitches with an oscilloscope on the 10 Ohm resistor.
Measure the expected delay and glitch length with the oscilloscope.

## More Examples

More examples can be found on [https://fault-injection-library.readthedocs.io/en/latest/examples/#](https://fault-injection-library.readthedocs.io/en/latest/examples/#) or under `fault-injection-library/projects`.

## Analyzer

During your glitching campaign, run the `analyzer` script in a separate terminal window:

```bash
analyzer --directory databases
```

This spins up a local web application on [http://127.0.0.1:8080](http://127.0.0.1:8080) which can be used to observe the current progress.

![Parameter space web application](https://github.com/MKesenheimer/fault-injection-library/blob/master/docs/images/parameterspace-pico-glitcher.png)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=MKesenheimer/fault-injection-library&type=Date)](https://star-history.com/#MKesenheimer/fault-injection-library&Date)