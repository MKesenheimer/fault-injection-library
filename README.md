# Usage with examples

This library is intended to make fault injection attacks against microcontrollers accessible for hobbyists and to introduce the topic of voltage glitching.
This software offers an easy entry point to carry out your own attacks against microcontrollers, SoCs and CPUs.
With the provided and easy to use functions and classes, fault injection projects can be realized quickly.

This library is based on [TAoFI-FaultLib](https://github.com/raelize/TAoFI-FaultLib).
However, several new features have been implemented.
For example, the original library was developed to work with the [ChipWhisperer-Husky](https://rtfm.newae.com/Capture/ChipWhisperer-Husky/) only.
This library has been rewritten to work with hardware that consists of a common MOSFET, the [Raspberry Pi Pico](https://www.raspberrypi.com/products/raspberry-pi-pico/) as the controlle and a few other cheap parts.
The Raspberry Pi Pico is not only cheap and available for the hobbyist, but also a very capable microcontroller.

Furthermore, the database functionality has been expanded to a certain extent.
With this implementation, e.g. one can add experiments to a previous measurement.

More features are planned in the future.
For example support for the [ChipWhisperer-Husky](https://rtfm.newae.com/Capture/ChipWhisperer-Husky/) and the [ChipWhisperer Pro](https://rtfm.newae.com/Capture/ChipWhisperer-Pro/) is added.

## Cloning

Set up the project by cloning it:
```bash
git clone --recurse-submodules
cd fault-injection-lib
```

## Setting up a virtual environment

If you want to make sure that the libraries to be installed do not collide with your installed Python environment, use a virtual environment.
Set it up by generating a new virtual environment and by activating it:
```bash
python -m venv .venv
source .venv/bin/activate
```

## Installing dependencies

After these steps we have to install some requirements via pip.
Make sure to have pip [installed](https://docs.python.org/3/library/ensurepip.html).
```bash
pip install -r requirements.txt
```

## Installing micropython scripts on the Raspberry Pi Pico

Now we have to prepare the Raspberry Pi Pico.
Add the [Micropython firmware](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico/3).
In general the following script can be used to upload Micropython scripts to the Raspberry Pi Pico.
```bash
python lib/upload-micro-python.py --port /dev/<rpi-tty-port> <script.py>
```

## Executing blink test

A simple example how the Micropython classes and functions are accessed on the Raspberry Pi Pico, the following "Hello World" program can be executed.
This can also be the first check, if everything is set up correctly.
```bash
cd blink
python ../lib/upload-micro-python.py --port /dev/<rpi-tty-port> --script mp_blink.py
python test.py --rpico /dev/tty.usbmodem11101
```

## Executing Raspberry Pi Pico glitcher example implementation

To carry out a fault injection attack with the Raspberry Pi Pico on another microcontroller, the following setup can be used.

First, we connect the Raspberry Pi Pico and a target as follows:
<TODO: Schematic>

We install the corresponding Micropython script on the Raspberry Pi Pico:
```bash
cd lib
python upload-micro-python.py --port /dev/<rpi-tty-port> --script mp_glitcher.py
```
Although the software is based on Micropython, using the PIO functions of the Raspberry Pi Pico, very precise switching operations can be made and triggered on external signals.

Next, we switch to the directory `pico-glitcher` and execute the script which controls our attack.
```bash
cd ../pico-glitcher
python pico-glitcher.py --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --delay 1_000 2_000 --length 100 150
```
The script resets the target, arms the pico glitcher, waits for the external trigger (reset high) and emits a glitch of a given length after a certain delay.
The response of the target is then read and classified.
The results are entered into a database, which can be processed in the browser using the command:
```bash
python ../analyzer/taofi-analyzer --directory databases
```
This attack can be used, for example, to bypass the read-out protection (RDP) of Apple Airtags and to download the firmware of these devices.
See [the video by stacksmashing](https://www.youtube.com/watch?v=_E0PWQvW-14) for more details.


## Executing STM32 bootloader glitching via the Raspberry Pi Pico glitcher

A more advanced attack is, for example, a fault injection attack against the STM32 bootloader and bypassing the read-out protection of these chips.
This attack has been first described by [SEC consult](https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/) and uses the [ChipWhisperer Pro](https://rtfm.newae.com/Capture/ChipWhisperer-Pro/) for the injection controller.
However, to glitch these devices successully, no expensive hardware is necessary, as it is demonstrated with the following scripts.

Connect the Raspberry Pi Pico and the STM32 target according to the following schematic:
<TODO: Schematic>

Install the Raspberry Pi Pico Micropython scripts:
```bash
cd lib
python upload-micro-python.py --port /dev/<rpi-tty-port> --script mp_glitcher.py
```
Next, change into `stm32-glitching` and execute the following script.
```bash
cd stm32-glitching
python stm32-glitching.py --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --delay 100_000 200_000 --length 100 150
```

Again, use the following command to analyze the collected datapoints:
```bash
python ../analyzer/taofi-analyzer --directory databases
```

If everything goes as expected, a successful run should look something like this:
![Bootloader glitching](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32-glitching/images/bootloader-glitching.png)


## Further handy features and notes

One can resume inserting datapoints into the database of the most recent run by supplying the `resume` flag:
```bash
python pico-glitcher.py ... --resume
```
