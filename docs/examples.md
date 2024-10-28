# Example Projects

Start your glitching career with these two examples.

## Test the functionality of your Pico Glitcher

The following  setup can be used to test the Pico Glitcher.

- Connect 'TRIGGER' input with 'RESET'.
- Between 'GLITCH' and 'VTARGET', connect a 10 Ohm resistor (this is the test target in this case).
- Optionally connect channel 1 of an oscilloscope to 'RESET' and channel 2 to 'GLITCH'.

![Example setup](images/test-example.png)

Next, run the test script `pico-glitcher.py` located in `fault-injection-library/example`:

```bash
cd example
python pico-glitcher.py --rpico /dev/<rpi-tty-port> --delay 1000 1000 --length 100 100
```

You should now be able to observe the glitches with an oscilloscope on the 10 Ohm resistor.
Measure the expected delay and glitch length with the oscilloscope.


## Airtag Glitching

It has already been shown by other works ([Stacksmashing](https://youtu.be/_E0PWQvW-14?si=zNzqpAz84Lce6TEz), [Adam Catley](https://adamcatley.com/AirTag.html), [Colin O'Flynn](https://colinoflynn.com/tag/airtag/)) that the chip installed on the Airtag, the nrf52832, is susceptible to voltage glitching attacks. The setup for the voltage glitching attack with the Pico Glitcher is as follows:

![Airtag Glitching](images/airtag-glitching.png)

To ensure that the correct voltage levels are available to the Segger J-Link, a level converter is inserted between the Airtag and J-Link. Voltage levels of 1.8V are required on the Airtag side and 3.3V on the J-Link side. The Pico Glitcher's voltage generation capabilities can be used to generate the different voltage levels.

The colors of the connections encode these signals:

- red: VTARGET, supply voltage of the air tag (3.3V)
- brown: VRef, reference voltage for the level shifter (1.8V)
- black: GND
- green: Trigger line, connected to 1.8V of the airtag. If this line is supplied with voltage, the trigger is set.
- purple: Glitch, connected to VCORE of the airtag. This is the power supply of the nrf52832

An oscilloscope on 'VTARGET' and 'VCORE' is also used to monitor the fault-injection campaign and to narrow down the 'delay' paremeter. The following figures show the voltage curve of 'VTARGET' (blue) and 'VCORE' (yellow). The fine voltage drop in VCORE after about 4.5ms after activating the power supply is striking. This area is interesting for gliching attacks, as the microcontroller nrf52832 switches from the bootloader to the user program (application) and has a higher energy consumption after this switch. Shortly before this switch, a check is made to see whether read-out protection is set. Glitches are therefore set around the 4.5ms mark.

![Voltage trace](images/voltage-trace.png)

![Glitch](images/glitch-1.png)

The magnitude of the glitch length is estimated from the processor frequency. For the nrf52832 this is 64 MHz, i.e. one CPU cycle takes approx. 16 ns. However, as other components such as capacitors or even the supply lines can change the "sharpness" of the glitch, a multiple of this duration is selected as the starting point. The glitch duration must not be too long, otherwise the microcontroller will be driven into reset. A glitch duration of 300 ns is selected initially.

The script `nrf52832-glitching.py` located at `projects/nrf52832-glitching` (or [here](https://github.com/MKesenheimer/fault-injection-library/blob/master/projects/nrf52832-glitching)) is used to perform the glitching campaign. After connecting the Pico Glitcher to the Airtag according to the schematics, run the following commands to start glitching:

```bash
cd fault-injection-library/projects/nrf52832-glitching
python pico-glitcher.py --rpico /dev/<rpi-tty-port> --delay 300 600 --length 3_300_000 3_600_000
```

Note, in order to communicate with the Airtag over SWD, [openocd](https://openocd.org) must be installed. Additionally, the script [testnrf.cfg](https://github.com/MKesenheimer/fault-injection-library/blob/master/projects/nrf52832-glitching/testnrf.cfg) must be in the root directory of the script `pico-glitcher.py`.
During the glitching campaign, run the `analyzer` script in a separate terminal window:

```bash
analyzer --directory databases
```

This spins up a local web application on [http://127.0.0.1:8080](http://127.0.0.1:8080) which can be used to observe the current progress.

![Parameter space web application](images/parameterspace-pico-glitcher.png)

The successful glitch and dump of the Airtag's flash content can be seen in the following figures.

![Successful glitch](images/command-line-pico-glitcher.png)

![Successful dump](images/dump-pico-glitcher.png)

### Details of the script nrf52832-glitching.py 

After initializing the glitcher, setting up the database and the logging mechanism, a random point from the parameter space is rolled in an endless loop from the arguments passed. The advantage of rolling a random parameter point is that a successful glitch can be achieved more quickly, even if a large range is tested. It also gives a quicker overview of interesting areas. The 'glitcher.arm' function arms the glitcher and waits until the trigger condition occurs.

```bash
# set up glitch parameters (in nano seconds) and arm glitcher
length = random.randint(s_length, e_length)
delay = random.randint(s_delay, e_delay)
self.glitcher.arm(delay, length)
```

The target is then restarted (power-cycled), which triggers the glitch. The glitch is sent after the time 'delay' with the duration 'length'. The function `test_jtag()` is used to check whether the nrf52832 can be interacted with on the SWD interface and, if so, the flash content is downloaded.

```bash
# power cycle target
self.glitcher.power_cycle_target(0.08)
 
# block until glitch
try:
    self.glitcher.block(timeout=1)
    # dump memory
    response = test_jtag()
except Exception as _:
    print("[-] Timeout received in block(). Continuing.")
    self.glitcher.power_cycle_target(power_cycle_time=1)
    time.sleep(0.2)
    response = b'Timeout'
```

The following commands are used to characterize the response of the target via SWD and the parameter point is inserted into the database in the corresponding color.

```bash
# classify response
color = self.glitcher.classify(response)

# add to database
self.database.insert(experiment_id, delay, length, color, response)
```

## More examples

More example projects can be found at [https://github.com/MKesenheimer/fault-injection-library/tree/master/projects](https://github.com/MKesenheimer/fault-injection-library/tree/master/projects) or under `fault-injection-library/projects` if you cloned the whole repository.
