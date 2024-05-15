# Usage with examples

This library is based on [TAoFI-FaultLib](https://github.com/raelize/TAoFI-FaultLib)

## Cloning

```bash
git clone --recurse-submodules
cd fault-injection-lib
```

## Setting up a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Install micropython scripts on the Raspberry Pi Pico

```bash
python lib/upload-micro-python.py --port /dev/<rpi-tty-port> <script.py>
```

## Execute blink test

```bash
cd blink
python ../lib/upload-micro-python.py --port /dev/<rpi-tty-port> --script mp_blink.py
python test.py --rpico /dev/tty.usbmodem11101
```

## Execute Raspberry Pi Pico glitcher example implementation

```bash
cd lib
python upload-micro-python.py --port /dev/<rpi-tty-port> --script mp_glitcher.py
cd pico-glitcher
python pico-glitcher.py --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --delay 1_000 2_000 --length 100 150
python ../analyzer/taofi-analyzer --directory databases
```

TODO: Schematic

## Execute STM32 bootloader glitching via the Raspberry Pi Pico glitcher

```bash
cd lib
python upload-micro-python.py --port /dev/<rpi-tty-port> --script mp_glitcher.py
cd stm32-glitching
python stm32-glitching.py --target /dev/<target-tty-port> --rpico /dev/<rpi-tty-port> --delay 1_000 2_000 --length 100 150
python ../analyzer/taofi-analyzer --directory databases
```

TODO: Schematic
