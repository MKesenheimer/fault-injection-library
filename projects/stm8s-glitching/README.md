#

## Prerequisites

stm8flash

```
git clone https://github.com/vdudouyt/stm8flash.git
cd stm8flash
make
sudo make install
```

Small Device C Compiler:

```
brew install sdcc
```

stm8-bootloader

```
git clone https://github.com/lujji/stm8-bootloader
cd stm8-bootloader
make
make flash
```

## Commands to flash the target

Unlock the device (erases the flash):

```
stm8flash -c stlinkv2 -p stm8s003f3 -u
```

Write image to flash:

```
stm8flash -c stlinkv2 -p stm8s003f3 -w blink.bin
```

Read image from flash:

```
stm8flash -c stlinkv2 -p stm8s003f3 -r dump.bin
```

Set Read-Out Protection (ROP):

```
echo -ne '\xaa' > rop_enable.bin
stm8flash -c stlinkv2 -p stm8s003f3 -s opt -w rop_enable.bin
```

Read option bytes:

```
stm8flash -c stlinkv2 -p stm8s003f3 -s opt -r opt_bytes.bin && xxd opt_bytes.bin
```

