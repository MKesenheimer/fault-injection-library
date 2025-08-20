# Attacking the ATMEGA328P

## Setup

![](setup.png)

### Wiring

![](avrisp-pinout.jpg)
Wire JTAGICE3 ISP pins to the ATmega328P:

```
MISO → MISO (PB4)
MOSI → MOSI (PB3)
SCK → SCK (PB5)
RESET → RESET
VCC → VCC
GND → GND
```

## Programming and Reading

The following commands can be used to program the chip, set the lock bits and read from flash:

### Programming

Write program to flash:

```bash
avrdude -p atmega328p -c jtag3isp -P usb -U flash:w:test.hex:i
avrdude -p m328p -c jtag3isp -P usb -U flash:w:test.hex:i
```

Setting fuses:

* Low fuse (lfuse): 0xFF -> external crystal, no CKDIV8
* High fuse (hfuse): 0xDE -> SPIEN enabled, bootloader reset + 0.5 KB boot section, EESAVE not set
* Extended fuse (efuse): 0x05 -> sets brown-out detection at 2.7 V

```bash
avrdude -p m328p -c jtag3isp -P usb \
  -U lfuse:w:0xFF:m \
  -U hfuse:w:0xDE:m \
  -U efuse:w:0x05:m # or 0xFD on newer avrdude
```

### Enable readout protection

* 0xFF = unlocked (default)
* 0x00 = full lock (chip only erasable, not readable)
* 0xFC = no programming, no verify/read (strongest: code protected)

```bash
avrdude -p m328p -c jtag3isp -P usb -U lock:w:0x00:m
```

### Disable readout protection and erase flash

```bash
avrdude -p m328p -c jtag3isp -P usb -e
```

### Reading

Dump flash:
```bash
avrdude -p m328p -c jtag3isp -P usb -U flash:r:dump.hex:i
```

Read fuses:
```bash
avrdude -p m328p -c jtag3isp -P usb -U lfuse:r:lfuse.hex:h -U hfuse:r:hfuse.hex:h -U efuse:r:efuse.hex:h
```

Read lock bits:
```bash
avrdude -p m328p -c jtag3isp -P usb -U lock:r:lock.hex:h
```
