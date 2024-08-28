# Notes

## Short Summary
- Capacitors V_CAP_1 and V_CAP_2 have to be removed. Glitch is inserted on V_CAP line.
- Successful glitches and memory dumps in the following parameter range (ChipWhisperer Pro):
```bash
python pro-glitcher.py --target /dev/<target-tty-port> --delay 90_500 91_500 --length 230 240
```
- Flash gets erased occasionally while glitching -> target has to be reprogrammed.
- PCROP register gets set occasionally while glitching -> bootloader memory responses are masked with zeros.
- PCROP register must be unset if it is set during a glitching attempt.
- Bootloader code (address 0x1fff0000) can be dumped and reverse engineered.
- [AN2606 Application note STM32 microcontroller system memory boot mode](https://www.st.com/resource/en/application_note/an2606-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf)

![Glitch insertion point](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32l0-glitching/images/power_supply_scheme.png)
[AN4488 Application note](https://www.st.com/resource/en/application_note/an4488-getting-started-with-stm32f4xxxx-mcu-hardware-development-stmicroelectronics.pdf)

![](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32f4-glitching/images/memory_dump.png)

![](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32f4-glitching/images/programmed_memory.png)

![](https://github.com/MKesenheimer/fault-injection-library/blob/master/stm32f4-glitching/images/cw-pro-bootloader-glitching.png)

## TODO
- [ ] Screenshot of set PCROP register
- [ ] STM32F4 glitching with new development board (STM black pill STM32F401CCU6), see [STM32F401CCU6 glitching](https://jerinsunny.github.io/stm32_vglitch/)
- [ ] Screenshot of oscilloscope
- [ ] Dump and reverse engineering of Bootloader
- [ ] Document results