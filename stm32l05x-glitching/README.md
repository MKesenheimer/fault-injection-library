# Notes

## Short Summary
- All decoupling capacitors have to be removed. Glitch is inserted directly on the power line.
- Successful glitches and memory dumps in the following parameter range (ChipWhisperer Pro):
```bash
python pro-glitcher.py --target /dev/<target-tty-port> --power /dev/<rd6006-tty-port> --delay 94_000 96_000 --length 100 120
```
- Flash gets erased occasionally while glitching (0.1% of all attempts) -> target has to be reprogrammed.
- STM32L0 behaves differently then the STM32F4 in bootloader mode:
- if RDP1 is set, bootloader resets the microcontroller after the numbers of bytes were transmitted.
- Bootloader (address 0x1FF00000) can not be dumped as the memory (even in RDP0) is protected.
- [AN2606 Application note STM32 microcontroller system memory boot mode](https://www.st.com/resource/en/application_note/an2606-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf)

![Glitch insertion point](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32l05x-glitching/images/power_supply_scheme.png)
[AN4488 Application note](https://www.st.com/resource/en/datasheet/stm32l052c6.pdf)

![](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32l05x-glitching/images/cw-pro-bootloader-glitching.png)

![](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32l05x-glitching/images/1-init-bootloader.png)

![](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32l05x-glitching/images/2-memread-cmd.png)

![](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32l05x-glitching/images/4-number-of-bytes-cmd.png)

## TODO
- [ ] Screenshot of oscilloscope
- [ ] Try to dump the bootloader and reverse engineer it.
- [ ] Add the Mouser/JLCPCB parts list to the resources.
- [ ] Add Toed as contributor
- [ ] Document PCB development on hackaday.io, hackster.io, instructables.com, deralchemist.wordpress.com
- [ ] Document results