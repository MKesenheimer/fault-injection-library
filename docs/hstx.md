# HSTX high-resolution glitching

The RP2350-based Pico Glitcher v3 can use the
[RP2350 HSTX peripheral](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf)
to generate a crowbar control pulse with two timing steps per system-clock
cycle. The firmware keeps the existing 250 MHz system clock, so the HSTX
timing quantum is:

```text
1 / (2 × 250 MHz) = 2 ns
```

Consequently, `delay` and `length` must be exact multiples of 2 ns. A 2.5 ns
pulse is not representable at 250 MHz; it would require a 200 MHz system clock.
The electrical pulse seen at the target also depends on the MOSFET, gate drive,
wiring, load and oscilloscope bandwidth, so measure the result at the target
rail rather than assuming the digital timing is the analogue pulse width.

## Using HSTX mode

Install this checkout and its 1.15.0 firmware for a Pico Glitcher v3:

```shell
python -m pip install -e .
update-fw --port /dev/<rpi-tty-port> --version v3.0
```

Then use `arm_hstx()` instead of `arm()`:

```python
from findus import PicoGlitcher

glitcher = PicoGlitcher()
glitcher.init(port="/dev/ttyACM0")
glitcher.rising_edge_trigger(dead_time=0)
glitcher.set_lpglitch()

glitcher.arm_hstx(delay=100, length=2)
glitcher.reset_target(0.01)
glitcher.block(timeout=1)
```

Falling-edge triggering works with `falling_edge_trigger(dead_time=0)`. The
implementation reserves PIO1 for the waveform and samples the configured
trigger pin directly. Leave the standard glitch state machines on their
default PIO0. HSTX mode currently supports one pulse, direct `tio` edge
triggering, and a zero trigger dead zone. UART triggering, edge-count
triggering, bursts, double glitches and a trigger dead zone remain available
through the standard glitching methods, not `arm_hstx()`.

The pulse waveform is 32 half-cycles wide. At 250 MHz, the largest pulse is 64
ns when its delay is an even number of half-cycles, or 62 ns when it starts on
the second half-cycle. Longer trigger-to-pulse delays are supported; only the
pulse itself and its half-cycle alignment occupy this waveform window.

HSTX coupled mode is specified by Raspberry Pi for at most a 150 MHz HSTX
clock. Since coupled mode takes its clock directly from the system clock, this
250 MHz use is outside the published HSTX timing specification. Treat the mode
as experimental and verify every board with an oscilloscope.

## Experimental 300 MHz operation

The optional **300 MHz** clock can be requested after initialization:

```python
glitcher.init(port="/dev/ttyACM0")
glitcher.set_cpu_frequency(300_000_000)
print(glitcher.get_cpu_frequency())
```

At 300 MHz the HSTX quantum is approximately 1.6667 ns. For example, a 5 ns
pulse is exactly three half-cycles:

```python
glitcher.rising_edge_trigger(dead_time=0)
glitcher.set_lpglitch()
glitcher.arm_hstx(delay=100, length=5)
```

This is an unsupported system-clock and HSTX overclock. Start without a target,
confirm the reported frequency, check the waveform and trigger alignment on an
oscilloscope, and watch for USB, flash or PIO instability. Return to the current
project default with:

```python
glitcher.set_cpu_frequency(250_000_000)
```

A reset or power cycle also returns this firmware to its configured 250 MHz
startup clock.
