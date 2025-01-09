class PulseGenerator():
    def __init__(self, time_resolution:int = 10):
        # all units in [ns] and [V]
        if time_resolution < 6:
            raise Exception("Error: time_resolution too small.")
        self.time_resolution = time_resolution
        self.frequency = 1_000_000_000 / self.time_resolution
        self.max_points = 4096
        self.points_per_ns = 1 / self.time_resolution
        voltage_resolution = 4096
        max_voltage = 5.0
        self.points_per_volt = int(voltage_resolution / max_voltage)
        #print(f"Points per volt: {self.points_per_volt}")
        self.pulse_constant = []

    def calculate_pulse_number_of_points(self, total_pulse_duration:int) -> int:
        pulse_number_of_points = int(total_pulse_duration / self.time_resolution)
        if pulse_number_of_points > self.max_points:
            return self.max_points
        return pulse_number_of_points

    def get_frequency(self):
        return self.frequency

    def get_max_points(self):
        return self.max_points

    def pulse_from_config(self, ps_config:list[list[int]], padding:bool = False) -> list[int]:
        pulse = []
        for point in ps_config:
            t = point[0]
            v = point[1]
            n = int(t * self.points_per_ns)
            value = int(v * self.points_per_volt)
            pulse += [value] * n
        # padding with last value
        if padding:
            length = len(pulse)
            if length < self.max_points:
                last_value = pulse[-1]
                pulse += [last_value] * (self.max_points - length)
        # sanity check
        if len(pulse) > self.max_points:
            raise Exception("Erroneous pulse config: pulse too large.")
        return pulse

    def pulse_from_lambda(self, ps_lambda, total_pulse_duration:int, padding:bool = False) -> list[int]:
        pulse_number_of_points = self.calculate_pulse_number_of_points(total_pulse_duration)
        pulse = [0] * pulse_number_of_points
        t = 0
        dt = self.time_resolution
        for i in range(pulse_number_of_points):
            pulse[i] = int(ps_lambda(t) * self.points_per_volt)
            t += dt
        # padding with last value
        if padding:
            if pulse_number_of_points < self.max_points:
                last_value = pulse[-1]
                pulse += [last_value] * (self.max_points - pulse_number_of_points)
        return pulse

    def pulse_from_list(self, pulse:list[int], padding:bool = False) -> list[int]:
        # padding with last value
        if padding:
            length = len(pulse)
            if length < self.max_points:
                last_value = pulse[-1]
                pulse += [last_value] * (self.max_points - length)
        # sanity check
        if len(pulse) > self.max_points:
            raise Exception("Fatal error: pulse too large.")
        return pulse

    def predefined_pulse1_constant(self, vstart:float, tramp:int, vstep:float, tstep:int):
        # this part of the pulse must be calculated only once and can be stored
        pulse_constant = []
        if tramp > 0:
            # trunk-ignore(ruff/E731)
            ramp_lambda = lambda t: (vstep - vstart) / tramp * t + vstart
            nramp = self.calculate_pulse_number_of_points(tramp)
            ramp = [0] * nramp
            t = 0
            dt = self.time_resolution
            for i in range(nramp):
                ramp[i] = int(ramp_lambda(t) * self.points_per_volt)
                t += dt
            pulse_constant += ramp
        nstep = int(tstep * self.points_per_ns)
        value = int(vstep * self.points_per_volt)
        pulse_constant += [value] * nstep
        self.pulse_constant = pulse_constant

    def predefined_pulse1(self, vstart:float, tramp:int, vstep:float, tstep:int, length:int, vend:float, recalc_constant:bool = False, padding:bool = False) -> list[int]:
        if self.pulse_constant == [] or recalc_constant:
            self.predefined_pulse1_constant(vstart, tramp, vstep, tstep)
        pulse = self.pulse_constant.copy()
        nlength = int(length * self.points_per_ns)
        pulse += [0] * nlength
        pulse += [(int(vend * self.points_per_volt))]
        # padding with last value
        if padding:
            length = len(pulse)
            if length < self.max_points:
                last_value = pulse[-1]
                pulse += [last_value] * (self.max_points - length)
        # sanity check
        if len(pulse) > self.max_points:
            raise Exception("Error: pulse too large.")
        return pulse

    def pulse_from_predefined(self, ps_config:dict, recalc_const:bool = False, padding:bool = False) -> list[int]:
        pulse = []
        if ps_config["psid"] == 1:
            if self.pulse_constant == [] or recalc_const:
                pulse = self.predefined_pulse1(ps_config["vstart"], ps_config["tramp"], ps_config["vstep"], ps_config["tstep"], ps_config["length"], ps_config["vend"], True, padding)
            else:
                pulse = self.predefined_pulse1(0.0, 0, 0.0, 0, ps_config["length"], ps_config["vend"], False, padding)
        return pulse