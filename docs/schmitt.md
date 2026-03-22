# Schmitt Trigger EXT inputs

The trigger inputs `EXT1` and `EXT2` are particularly useful for noisy logic signals, as the noise can be easily suppressed by the adjustable Schmitt Trigger.
If, for example, the signal oscillates or is disturbed in any other way, this disturbances can be cut off by selecting a suitable threshold.

![](images/schmitt-trigger-inputs/schmitt-trigger-input-test.png)

Use the potentiometer labeled `THR` to adjust the threshold of the Schmitt Trigger.
The threshold is lowered by turning the potentiometer to the left (counter clock-wise).

The potentiometer `ATN` can be used for an additionally signal reduction, if necessary. Turning the potentiometer all the way to the right (clock-wise) disables attenuation and uses the full signal range.

Changes have been made in version 3 to the `EXT2` trigger input. Now the hysteresis of the trigger behavior can be adjusted.

![](images/schmitt-trigger-inputs/schmitt-triggers-v3.png)

The `HYS` potentiometer is used to adjust the hysteresis of the Schmitt trigger input `EXT2`. It controls the difference between the upper and lower switching thresholds. By changing this difference, it directly determines how much the input signal must move before the output changes state.

With no hysteresis, the Schmitt trigger switches at the same input level for both rising and falling edges. The output changes state exactly at a single threshold, making the circuit sensitive to noise and small fluctuations around that level.

When hysteresis is introduced, the switching point depends on the direction of the input signal. On a rising input, the signal must reach the upper threshold before the output changes, causing the transition to occur later than it would without hysteresis. On a falling input, the signal must drop below the lower threshold before switching back, which also delays the transition compared to a single-threshold comparator.

Increasing the hysteresis widens the gap between the upper and lower thresholds. This makes the circuit switch later on both rising and falling edges, relative to the no-hysteresis case. Reducing the hysteresis narrows this gap, bringing the two switching points closer together until they coincide when hysteresis is effectively zero.

This behavior is what gives the Schmitt trigger its noise immunity: small variations around the switching level do not cause repeated transitions, and the exact timing of state changes can be deliberately shifted by adjusting the hysteresis.

The schematics of the new Schmitt trigger inputs can be seen below.

![](images/schmitt-trigger-inputs/schematic.png)

## How to set the potentiometers

The `ATN` potentiometers should be turned clock-wise completely to the right to use the full signal range.
If you have trigger signals that exceed the voltage range of the Pico Glitcher (max. `5V`), use the `ATN` potentiometers to bring down the input signals to a range that is acceptable by the Raspberry Pi Pico.

By turning the `THR` potentiometer counter clock-wise to the left, the threshold is lowered, meaning the Pico Glitcher triggers at lower signals. Start the `THR` potentiometer at the highest threshold position (right), then lower it (turn it counter clock-wise) until the trigger is observed.

Use the `HYS` potentiometer in the same way as the `THR` potentiometer. Start the `HYS` potentiometer at the highest threshold position (right), then lower it (turn it counter clock-wise) until the trigger is observed.

Which trigger input to use (`EXT1` or `EXT2`) depends on your setup and how messy your trigger signal is. Try each trigger setup and decide which input works best for your setup.

If you have set the potentiometers for one setup, don't change them until you have completed your glitching campaign. Changing the threshold values can mess with your glitching parameters (especially with the `delay` value).