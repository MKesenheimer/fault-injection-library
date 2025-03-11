#

## Prerequisites

stm8flash

```bash
git clone https://github.com/vdudouyt/stm8flash.git
cd stm8flash
make
sudo make install
```

Small Device C Compiler:

```bash
brew install sdcc
```

stm8-bootloader

```bash
git clone https://github.com/MKesenheimer/stm8-bootloader.git
cd stm8-bootloader
make
make flash
```

## Commands to flash the target via stm8flash

Unlock the device (erases the flash):

```bash
stm8flash -c stlinkv2 -p stm8s003f3 -u
```

Write image to flash:

```bash
stm8flash -c stlinkv2 -p stm8s003f3 -w blink.bin
```

Read image from flash:

```bash
stm8flash -c stlinkv2 -p stm8s003f3 -r dump.bin
```

Set Read-Out Protection (ROP):

```bash
echo -ne '\xaa' > rop_enable.bin
stm8flash -c stlinkv2 -p stm8s003f3 -s opt -w rop_enable.bin
```

Read option bytes:

```bash
stm8flash -c stlinkv2 -p stm8s003f3 -s opt -r opt_bytes.bin && xxd opt_bytes.bin
```

## Commands to flash the target using the Makefile

Unlock the device (erases the flash):

```bash
make reset-opt
```

Write image to flash:

```bash
make flash
```

Read image from flash:

```bash
make dump-flash
```

Set Read-Out Protection (ROP):

```bash
make enable-rop
```

Read option bytes:

```bash
make dump-opt
```
