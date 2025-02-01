# Using the analog digital converter

Setup:
```python
from findus import AnalogPlot

# initialization
glitcher = DerivedGlitcher()
...

# plot the voltage trace while glitching
number_of_samples = 1024
sampling_freq = 450_000
glitcher.configure_adc(number_of_samples=number_of_samples, sampling_freq=sampling_freq)
plotter = AnalogPlot(number_of_samples=number_of_samples, sampling_freq=sampling_freq)
```

In glitch loop:
```python
while True:
    # arming and other stuff
    ...

    # arm the adc
    glitcher.arm_adc()

    # triggering and reading the targets response
    ...

    # plotting the analog samples
    samples = glitcher.get_adc_samples()
    plotter.update_curve(samples)
```

See for example `fault-injection-library/examples/pico-glitcher.py`:

```bash
python pico-glitcher.py --rpico /dev/tty.usbmodem1101 --delay 1000000 1000000 --length 1000 1000
```

![Alt text](images/adc/adc.png)