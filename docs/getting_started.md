# Getting Started

This guide should quickly prepare you to use the Pico Glitcher and the findus library.

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

### Step 2: Download the Pico Glitcher firmware

Together with the findus library comes the MicroPython script (the "Pico Glitcher firmware"), which must be installed on the Pico Glitcher. Download the latest Pico Glitcher firmware here: [https://github.com/MKesenheimer/fault-injection-library/blob/master/findus/mpGlitcher.py](https://github.com/MKesenheimer/fault-injection-library/blob/master/findus/mpGlitcher.py).

Alternatively, if you installed findus from source (see [here](#building-from-source)), the Pico Glitcher firmware can be found at `fault-injection-library/findus/mpGlitcher.py`.

### Step 3: Install the findus library

Skip this step, if you already installed findus previously (see [here](#installing-findus)).

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

### Step 4: Upload the Pico Glitcher MicroPython script

If everything went well, you should have the `upload` script available for execution in your command-line environment.
Connect the Pico Glitcher to your computer and check which serial device comes up:

```bash
ls /dev/tty*
```

Take note of the device path. Next upload `mpGlitcher.py` and the specific configuration for your Pico Glitcher hardware version via the following command:

```bash
cd findus
upload --port /dev/<rpi-tty-port> --script mpGlitcher.py
upload --port /dev/<rpi-tty-port> --script mpConfig_vx/config.json
```

Your Pico Glitcher should now be ready to perform fault-injection attacks.

## Building from source

If you want to get involved in the development or to have access to all the resources of this repository, clone the findus library:

```bash
git clone --depth 1 --recurse-submodules https://github.com/MKesenheimer/fault-injection-library.git
```

Install the findus and the optional rd6006 library:

```bash
cd fault-injection-library
pip install .
cd rd6006
pip install .
```

The next step is to copy an existing glitching script and to adapt it to your needs.
Start by copying `fault-injection-library/example/pico-glitcher.py`. More example projects are located at `fault-injection-library/projects`.

See [examples](examples.md) for more information how to use findus and the Pico Glitcher.
