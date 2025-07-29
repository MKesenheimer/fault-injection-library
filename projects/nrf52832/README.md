# Notes

## Short Summary

The following attacks are WiP and parameters may not be final.

Attacking a keyboard with nrf52832 chip:
```
python nrf52832-glitching.py --rpico /dev/ttyACM1 --delay 1_000_000 1_300_000 --length 300 600
```

Attacking an Apple Airtag with nrf52832 chip:
```
python nrf52832-glitching.py --rpico /dev/ttyACM1 --delay 4_300_000 4_600_000 --length 300 600
```


## TODO
- [x] Develop scripts
- [ ] Document results