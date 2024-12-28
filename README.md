# Usage with examples

Findus (aka the fault-injection-library) is a toolchain to perform fault-injection attacks on microcontrollers and other targets.
This library offers an easy entry point to carry out fault-injection attacks against microcontrollers, SoCs and CPUs.
With the provided and easy to use functions and classes, fault-injection projects can be realized quickly with cheap and available hardware.

Findus supports the [ChipWhisperer Pro](https://rtfm.newae.com/Capture/ChipWhisperer-Pro/), the [ChipWhisperer Husky](https://rtfm.newae.com/Capture/ChipWhisperer-Husky/) and the PicoGlitcher.
More information about the ChipWhisperer Pro and the ChipWhisperer Husky can be found on [https://chipwhisperer.readthedocs.io/en/latest/index.html](https://chipwhisperer.readthedocs.io/en/latest/index.html).

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
upload --port /dev/<rpi-tty-port> --script <script.py>
```

## Executing Raspberry Pi Pico glitcher example implementation

To carry out a fault injection attack with the Raspberry Pi Pico on another microcontroller, the following setup can be used.

First, we connect the Pico Glitcher and a target as follows:
![Example usage](https://github.com/MKesenheimer/fault-injection-library/blob/master/schematics/fritzing/esp32-glitching.png)
Note that the trigger input is connected directly to the reset line.
As the reset is released from the device, the trigger signal is sent.

We install the corresponding Micropython script and the corresponding config file (must be done only once) on the Raspberry Pi Pico:

```bash
upload --port /dev/<rpi-tty-port> --delete-all
upload --port /dev/<rpi-tty-port> --script ./findus/mpConfig_v1/mpConfig.py
upload --port /dev/<rpi-tty-port> --script ./findus/mpGlitcher.py
```

For hardware version 2.x of the PicoGlitcher, the corresponding config file must be provided:

```bash
upload --port /dev/<rpi-tty-port> --delete-all
upload --port /dev/<rpi-tty-port> --script ./findus/mpConfig_v2/mpConfig.py
upload --port /dev/<rpi-tty-port> --script ./findus/mpGlitcher.py
```

Although the software is based on Micropython, using the PIO functions of the Raspberry Pi Pico, very precise switching operations can be made and triggered on external signals.

Next, we switch to the directory `example` and execute the script which controls our attack.

```bash
cd example
python pico-glitcher.py --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --delay 1_000 2_000 --length 100 150
```

The script resets the target, arms the pico glitcher, waits for the external trigger (reset high) and emits a glitch of a given length after a certain delay.
The response of the target is then read and classified.
The results are entered into a database, which can be processed in the browser using the command:

```bash
analyzer --directory databases
```

This attack can be used, for example, to bypass the read-out protection (RDP) of Apple Airtags and to download the firmware of these devices.
See [the video by stacksmashing](https://www.youtube.com/watch?v=_E0PWQvW-14) for more details.


## Attacking a STM32 bootloader via the Raspberry Pi Pico glitcher

A more advanced attack is, for example, a fault injection attack against the STM32 bootloader and bypassing the read-out protection of these chips.
This attack has been first described by [SEC consult](https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/) and uses the [ChipWhisperer Pro](https://rtfm.newae.com/Capture/ChipWhisperer-Pro/) for the injection controller.
However, to glitch these devices successully, no expensive hardware is necessary, as it is demonstrated with the following scripts.

Connect the Pico Glitcher and the STM32 target according to the following schematic:
![Example usage](https://github.com/MKesenheimer/fault-injection-library/blob/master/schematics/fritzing/stm32-glitching.png)
Here, the trigger line is connected to the UART-TX line, since we want to trigger on a specific UART word that is sent during the bootloader stage.
Furthermore, "Boot0" pin of the STM32 needs to be pulled high in order to activate the bootloader.
This pin is exposed on the Nucleo header.
In addition, due to the inherent limitations of the drawing program Fritzing, the glitching line was connected directly to 3.3V of the target in the schematics.
In a real setup, however, the glitching line should be soldered as close as possible to the power supply of the STM32 and the capacitors should be removed nearby.

Install the Raspberry Pi Pico Micropython scripts:

```bash
upload --port /dev/<rpi-tty-port> --script ./findus/mpConfig_v1/mpConfig.py
upload --port /dev/<rpi-tty-port> --script ./findus/mpGlitcher.py
```

Next, change into `projects/stm32f42x-glitching` and execute the following script.

```bash
cd projects/stm32f42x-glitching
python pico-glitcher.py --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --delay 100_000 200_000 --length 100 150
```

Or make use of the ChipWhisperer Pro by executing:

```bash
cd projects/stm32f42x-glitching
python pro-glitcher.py --target /dev/<target-tty-port> --delay 100_000 200_000 --length 100 150
```

Again, use the following command to analyze the collected datapoints:

```bash
analyzer --directory databases
```

If everything goes as expected, a successful run should look something like this:
![Bootloader glitching](https://github.com/MKesenheimer/fault-injection-library/blob/master/projects/stm32f42x-glitching/images/cw-pro-bootloader-glitching.png)

Refer to the README at `projects/stm32f42x-glitching` for more details.

## Further handy features and notes

One can resume inserting datapoints into the database of the most recent run by supplying the `resume` flag:

```bash
python pico-glitcher.py ... --resume
```

If the datapoints should not be inserted into the database, the flag `no-store` can be used instead:

```bash
python pico-glitcher.py ... --no-store
```

The flags `resume` and `no-store` can be combined.

## Pico Glitcher v1 hardware

As mentioned above, only a Raspberry Pi Pico and a few other components are required to use this software.
However, in order to achieve the best results, a circuit board was developed that was adapted directly for the fault-injection-library. 

The board consists of a Raspberry Pi Pico, two level shifters for in- and outputs with any voltage, and glitching transistors that can switch up to 66 amps.
![Pico Glichter v1](https://github.com/MKesenheimer/fault-injection-library/blob/master/schematics/kicad/pico-glitcher-v1/pico-glitcher-v1.1_sch.png)

There are several connection options for different voltage sources, from 1.8V, 3.3V to 5V.
The Pico Glitcher v1 can also be supplied with any external voltage via `VCC_EXTERN`.
To power the target board, it is supplied with power via the `VTARGET` connection.
The output of this voltage source can be controlled via the fault-injection-library, i.e. the target can be completely disconnected from power by executing the `helper/power-cycle-target.py` command.
This allows a cold start of the target to be carried out in the event of error states that cannot be eliminated by a reset.

The assembled and fully functional board is shown in the following figure:
![Assembled Pico Glitcher v1](https://github.com/MKesenheimer/fault-injection-library/blob/master/schematics/finished.JPG)
