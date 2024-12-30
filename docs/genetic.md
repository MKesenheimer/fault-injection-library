# Genetic Algorithm

In some cases, finding the parameters of a successful glitch can be quite tedious.
Especially if the possible parameter space is large (see [multiplexing](multiplexing.md) and [pulse-shaping](pulse_shaping.md)).

See for example `projects/esp32v1.3-glitching`.

```python
from findus import OptimizationController
```

classify-method with additional weight factors that are fed into the genetic algorithm.
```python
def classify(self, response):
    if b'read-out protection enabled\r\n' in response:
        color, weight = 'G', 0
    elif b'' == response:
        color, weight = 'M', 0
    elif b'Error' in response:
        color, weight = 'M', 0
    elif b'Fatal exception' in response:
        color, weight = 'M', 0
    elif b'Timeout' in response:
        color, weight = 'Y', -1
    else:
        color, weight = 'R', 2
    return color, weight
```

Bin definition:
```python
# Genetic Algorithm to search for the best performing bin
boundaries = [(s_delay, e_delay), (s_t1, e_t1), (s_length, e_length)]
divisions = [10, 10, 5]
opt = OptimizationController(parameter_boundaries=boundaries, parameter_divisions=divisions, number_of_individuals=10, length_of_genom=20, malus_factor_for_equal_bins
=1)
```

In the while-loop:
```python
# get the next parameter set
delay, t1, length = opt.step()
if experiment_id % 100 == 0:
    opt.print_best_performing_bins()

# perform arming, triggering, read response
[...]

# classify response
color, weight = glitcher.classify(response)

# add experiment to parameterspace of genetic algorithm
opt.add_experiment(weight, delay, t1, length)

```

Note that the implementation of the genetic algorithm is not specific to the Pico Glitcher and can therefore also be used by the ChipWhisperer Pro and Husky.
