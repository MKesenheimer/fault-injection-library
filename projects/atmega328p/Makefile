MCU = atmega328p
F_CPU = 16000000
CC = avr-gcc
OBJCOPY = avr-objcopy
CFLAGS = -Wall -Os -DF_CPU=$(F_CPU)UL -mmcu=$(MCU)

all: blink.hex

blink.elf: blink.c
	$(CC) $(CFLAGS) -o $@ $<

blink.hex: blink.elf
	$(OBJCOPY) -O ihex -R .eeprom $< $@

flash: blink.hex
	avrdude -F -c jtag3isp -p m328p -U flash:w:$<

protect:
	avrdude -F -c jtag3isp -p m328p -U lock:w:0x00:m

erase:
	avrdude -F -c jtag3isp -p m328p -e

read:
	avrdude -F -c jtag3isp -p m328p -U flash:r:dump.hex:i

read-lock:
	avrdude -F -c jtag3isp -p m328p -U lock:r:-:h

clean:
	rm -f blink.elf blink.hex