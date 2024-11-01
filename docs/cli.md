# Command-Line Tools

The following command-line tools are available after the installation of findus (`pip install findus`).

## upload

Tool to upload MicroPython scripts to the Pico Glitcher. This tool can be used, for example, to update the firmware of the Pico Glitcher.
Usage:

``` bash
$ upload --help
usage: upload [-h] [--port PORT] [--delete-all] [--script SCRIPT]

Upload a micro python script to the Raspberry Pi Pico.

options:
  -h, --help       show this help message and exit
  --port PORT      /dev/tty* of the Raspberry Pi Pico
  --delete-all     delete all micro python scripts from the Raspberry Pi Pico
  --script SCRIPT  micro python script to upload to the Raspberry Pi Pico
```

Examples:

- Upload or update an existing MicroPython script:
```bash
upload --port /dev/<rpi-tty-port> --script <script.py>
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
```

Example:
```bash
cd projects/airtag-glitching
analyzer --directory databases
```

Visit `http://127.0.0.1:8080` in your web browser to access the analyzer web application.
![Parameter space web application](images/parameterspace-pico-glitcher.png)

## bootloader-com

Communicate with a STM32 microcontroller in bootloader mode and read the flash memory (only if RDP-0 is active). If read-out protection is active, the corresponding target responses are printed.

Example:
```bash
bootloader-com /dev/<target-tty-port>
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