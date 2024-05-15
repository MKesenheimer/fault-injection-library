# Usage of fault-injection-library with examples

## Cloning
```
git clone --recurse-submodules
cd fault-injection-lib
```

## Setting up a virtual environment
```
python -m venv .venv
source .venv/bin/activate
```

## Install dependencies
```
pip install -r requirements.txt
```

## Install micropython scripts on the Raspberry Pi Pico
```
python lib/upload-micro-python.py --port /dev/<tty-port> <script.py>
```

## Execute blink test
```
cd blink
python ../lib/upload-micro-python.py --port /dev/tty.usbmodem21101 --script mp_blink.py
python test.py --rpico /dev/tty.usbmodem11101
```

## Execute raspberry pico glitcher
```
cd pico-glitcher
python ../lib/upload-micro-python.py --port /dev/tty.usbmodem21301 --script mp_glitcher.py
python pico-glitcher.py --target /dev/tty.usbserial-21101 --rpico /dev/tty.usbmodem21301 --delay 100_500 120_500 --length 100 150
python ../analyzer/taofi-analyzer --directory databases
```
