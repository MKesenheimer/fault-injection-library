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
usage: analyzer [-h] --directory DIRECTORY [--port PORT]

analyzer.py v0.1 - Fault Injection Analyzer

options:
  -h, --help            show this help message and exit
  --directory DIRECTORY
                        Database directory
  --port PORT           Server port
  --ip IP               Server address
```

Example:
```bash
cd projects/airtag-glitching
analyzer --directory databases
```

Visit `http://127.0.0.1:8080` in your web browser to access the analyzer web application.
![Parameter space web application](images/parameterspace-pico-glitcher.png)

Alternatively, you can spin up the web application on all network interfaces to access it from other hosts:

```bash
cd projects/airtag-glitching
analyzer --directory databases --ip 0.0.0.0
```

## bootloader-com

Communicate with a STM32 microcontroller in bootloader mode and read the flash memory (only if RDP-0 is active). If read-out protection is active, the corresponding target responses are printed.

Example:
```bash
bootloader-com /dev/<target-tty-port>
```

## power-on

Enable `VTARGET` with this simple script. Can be necessary, for example, to supply the target with power for debugging purposes.

```bash
power-on --help
usage: power-on [-h] [--rpico RPICO]

options:
  -h, --help     show this help message and exit
  --rpico RPICO  rpico port
```

Example:
```bash
power-on --rpico /dev/<rpi-tty-port>
```

## power-cycle-and-read

Test the power supply capabilities of your setup by executing this script. The target's response is read over UART after power-cycle.
If the argument `--rpico` is not supplied (no Pico Glitcher connected), the ChipWhisperer Pro is tried instead. 

```bash
power-cycle-and-read --help
usage: power-cycle-and-read [-h] [--target TARGET] [--rpico RPICO] [--dump]

options:
  -h, --help       show this help message and exit
  --target TARGET  target port
  --rpico RPICO    rpico port
  --dump
```

Example:

- Power cycle and read the target's response:
```bash
power-cycle-and-read --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port>
```

- Power cycle and dump the flash content of an STM32 target in bootloader mode (without read-out protection active):
```bash
power-cycle-and-read --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --dump
```

## power-cycle

Test the power supply capabilities of your setup by executing this script.
If the argument `--rpico` is not supplied (no Pico Glitcher connected), the ChipWhisperer Pro is tried instead.

```bash
power-cycle --help
usage: power-cycle [-h] [--rpico RPICO]

options:
  -h, --help     show this help message and exit
  --rpico RPICO  rpico port
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

A small tool to calibrate the digital-to-analog converter of the Pulse Shaping expansion board.

```bash
pulse-calibration --help
usage: pulse-calibration [-h] --rpico RPICO [--vhigh VHIGH] [--vlow VLOW]

options:
  -h, --help     show this help message and exit
  --rpico RPICO  rpico port
  --vhigh VHIGH
  --vlow VLOW
```

Execute the following command and follow the notes on the command line:
```bash
pulse-calibration --rpico /dev/<rpi-tty-port>
```
