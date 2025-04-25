# Command-Line Tools

The following command-line tools are available after the installation of findus (`pip install findus`).

## upload

Tool to upload MicroPython scripts to the Pico Glitcher. This tool can be used, for example, to update the firmware of the Pico Glitcher.
Usage:

``` bash
$ upload --help
usage: upload [-h] [--port PORT] [--delete-all] [--file FILE] [--files FILE1 FILE2...]

Upload a micro python script to the Raspberry Pi Pico.

options:
  -h, --help            show this help message and exit
  --port PORT           /dev/tty* of the Raspberry Pi Pico
  --delete-all          delete all files from the Raspberry Pi Pico
  --file FILE           file to upload to the Raspberry Pi Pico
  --files FILE1 FILE2   files to upload to the Raspberry Pi Pico
```

Examples:

- Upload or update an existing MicroPython script:
```bash
upload --port /dev/<rpi-tty-port> --file <file.py>
```

- Upload multiple files:
```bash
upload --port /dev/<rpi-tty-port> --files <file1.py> <file2.py>
```

- Delete all content:
```bash
upload --port /dev/<rpi-tty-port> --delete-all
```

## analyzer

Script that spins up a web application during a glitching campaign to observe the current progress. Must be executed in the directory where the glitching script is executed (this directory contains the `database` folder).

```bash
$ analyzer --help
usage: analyzer [-h] --directory DIRECTORY [--port PORT] [--ip IP] [-x X] [-y Y]
                [--aspect-ratio ASPECT_RATIO] [--auto-update [AUTO_UPDATE]] [--heatmap]
                [--x-number-of-bins X_NUMBER_OF_BINS] [--y-number-of-bins Y_NUMBER_OF_BINS]
                [--color-scale COLOR_SCALE]

analyzer.py v0.1 - Fault Injection Analyzer

options:
  -h, --help            show this help message and exit
  --directory DIRECTORY
                        Database directory
  --port PORT           Server port
  --ip IP               Server address
  -x X                  parameter to plot on the x-axis
  -y Y                  parameter to plot on the y-axis
  --aspect-ratio ASPECT_RATIO
                        aspect ratio of the plot relative to x-axis
  --auto-update [AUTO_UPDATE]
                        Whether to update the plot automatically. Optionally pass the update interval
                        in seconds.
  --heatmap             Generate a heat map
  --x-number-of-bins, --x-bins X_NUMBER_OF_BINS
                        Number of bins of the x-axis for the heat map
  --y-number-of-bins, --y-bins Y_NUMBER_OF_BINS
                        Number of bins of the y-axis for the heat map
  --color-scale COLOR_SCALE
                        Color scale to use for the heat map (findus, Blues, Reds, Greys, PuRd,
                        YlOrRd).
```

Example:
```bash
cd projects/airtag-glitching
analyzer --directory databases -x delay -y length
```

Visit `http://127.0.0.1:8080` in your web browser to access the analyzer web application.
![Parameter space web application](images/parameterspace-pico-glitcher.png)

Alternatively, you can spin up the web application on all network interfaces to access it from other hosts:

```bash
cd projects/airtag-glitching
analyzer --directory databases --ip 0.0.0.0
```

If you want to generate a heat map that shows the number of successful events in a region, use:

```bash
analyzer --directory databases --auto-update 60 --heatmap --x-bins 15 --y-bins 15 --color-scale findus
```

## stm32-bootloader

Communicate with a STM32 microcontroller in bootloader mode and read the flash memory (only if RDP-0 is active). If read-out protection is active, the corresponding target responses are printed.

Example:
```bash
stm32-bootloader /dev/<target-tty-port>
```

## stm8-programmer

Communicate with a STM8 microcontroller in bootloader mode and read the flash memory (only if RDP-0 is active). If read-out protection is active, the corresponding target responses are printed.

Example:
```bash
usage: stm8-programmer [-h] --port PORT [--baud BAUD] [--write WRITE] [--read READ] [--number-of-bytes NUMBER_OF_BYTES] [--write-option WRITE_OPTION]
                      [--read-option [READ_OPTION]]
```

## power-on

Enable `VTARGET` with this simple script. Can be necessary, for example, to supply the target with power for debugging purposes. Alternatively, the target device can also powered via the multiplexing stage, pulse-shaping stage or external power supply. If the `--rpico` argument is omitted (no Pico Glitcher connected), it will try to connect to the ChipWhisperer Pro instead.

```bash
power-on --help
usage: power-on [-h] [--rpico RPICO] [--power POWER] [--multiplexing] [--pulse-shaping] [--voltage VOLTAGE]

Power the target via different output stages of the Pico Glitcher (VTARGET, multiplexing stage, pulse-shaping stage or external power supply).

options:
  -h, --help         show this help message and exit
  --rpico RPICO      rpico port
  --power POWER      rk6006 port
  --multiplexing     Use the multiplexing stage to power the target (requires PicoGlitcher v2).
  --pulse-shaping    Use the pulse-shaping stage to power the target (requires PicoGlitcher v2). Be sure to calibrate the pulse-shaping stage's voltage output.
  --voltage VOLTAGE  The voltage to set. Note that the voltage output of the pulse-shaping stage can not be controlled with this parameter. The voltage output of the pulse-
                     shaping stage must be set manually with the potentiometer.
```

Example:
```bash
power-on --rpico /dev/<rpi-tty-port>
```

## stm32-power-cycle-and-read

Test the power supply capabilities of your setup by executing this script. The target's response is read over UART after power-cycle.
If the `--rpico` argument is omitted (no Pico Glitcher connected), it will try to connect to the ChipWhisperer Pro instead.

```bash
stm32-power-cycle-and-read --help
usage: stm32-power-cycle-and-read [-h] --target TARGET [--rpico RPICO] [--dump] [--power POWER] [--multiplexing] [--pulse-shaping] [--voltage VOLTAGE]

Power the target via different output stages of the Pico Glitcher (VTARGET, multiplexing stage, pulse-shaping stage or external power supply) and dump the flash content of a
STM32 in bootloader mode via a UART connection.

options:
  -h, --help         show this help message and exit
  --target TARGET    target port
  --rpico RPICO      rpico port
  --dump
  --power POWER      rk6006 port
  --multiplexing     Use the multiplexing stage to power the target (requires PicoGlitcher v2).
  --pulse-shaping    Use the pulse-shaping stage to power the target (requires PicoGlitcher v2). Be sure to calibrate the pulse-shaping stage's voltage output.
  --voltage VOLTAGE  The voltage to set. Note that the voltage output of the pulse-shaping stage can not be controlled with this parameter. The voltage output of the pulse-
                     shaping stage must be set manually with the potentiometer.
```

Example:

- Power cycle and read the target's response:
```bash
stm32-power-cycle-and-read --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port>
```

- Power cycle and dump the flash content of an STM32 target in bootloader mode (without read-out protection active):
```bash
stm32-power-cycle-and-read --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --dump
```

## power-cycle

Test the power supply capabilities of your setup by executing this script.
If the `--rpico` argument is omitted (no Pico Glitcher connected), it will try to connect to the ChipWhisperer Pro instead.

```bash
power-cycle --help
usage: power-cycle [-h] [--rpico RPICO] [--power POWER] [--multiplexing] [--pulse-shaping] [--voltage VOLTAGE]

Power-cycle the target via different output stages of the Pico Glitcher (VTARGET, multiplexing stage, pulse-shaping stage or external power supply).

options:
  -h, --help         show this help message and exit
  --rpico RPICO      rpico port
  --power POWER      rk6006 port
  --multiplexing     Use the multiplexing stage to power-cycle the target (requires PicoGlitcher v2).
  --pulse-shaping    Use the pulse-shaping stage to power-cycle the target (requires PicoGlitcher v2). Be sure to calibrate the pulse-shaping stage's voltage output.
  --voltage VOLTAGE  The voltage to set. Note that the voltage output of the pulse-shaping stage can not be controlled with this parameter. The voltage output of the pulse-
                     shaping stage must be set manually with the potentiometer.
```

Example:

- Power cycle via the Pico Glitcher:
```bash
power-cycle --rpico /dev/<rpi-tty-port>
```

- Power cycle via the ChipWhisperer Pro:
```bash
power-cycle
```

## pulse-calibration

A small tool to calibrate the digital-to-analog converter of the pulse-shaping expansion board.

```bash
pulse-calibration --help
usage: pulse-calibration [-h] --rpico RPICO [--vhigh VHIGH] [--vlow VLOW]

options:
  -h, --help     show this help message and exit
  --rpico RPICO  rpico port
  --vhigh VHIGH  The measured maximum voltage of the pulse.
  --vlow VLOW    The measured minimum voltage of the pulse.
```

Execute the following command and follow the notes on the command line:
```bash
pulse-calibration --rpico /dev/<rpi-tty-port>
```
