import matplotlib.pyplot as plt
import numpy as np

class AnalogPlot():
    """
    Class to easily plot captured voltage traces with the ADC.

    Example usage:

        from findus.AnalogPlot import AnalogPlot
        ...
        glitcher.configure_adc(number_of_samples=1024, sampling_freq=450_000)
        plotter = AnalogPlot(number_of_samples=1024, sampling_freq=450_000)
        ...
        glitcher.arm_adc()
        ...
        samples = glitcher.get_adc_samples()
        plotter.update_curve(samples)
    """
    def __init__(self, number_of_samples:int, vref:float = 3.3, sampling_freq = 500_000):
        self.number_of_samples = number_of_samples
        self.vref = vref
        self.sampling_freq = sampling_freq

        self.fig, self.ax = plt.subplots()
        plt.subplots_adjust(bottom=0.3)

        self.curve_line, = self.ax.plot([], [], label="Analog measurement", color="blue")

        x_end = 1_000_000_000 * self.number_of_samples / self.sampling_freq
        self.xpoints = np.linspace(0, x_end, self.number_of_samples)
        self.ypoints = np.zeros(self.number_of_samples)

        # Set axis limits and finer ticks
        self.ax.set_xlim(-1, x_end)
        self.ax.set_ylim(-0.2, 3.5)
        self.ax.set_xticks(np.arange(0, x_end, x_end / 10))
        self.ax.set_yticks(np.arange(0, 3.4, 0.5))

        self.ax.set_xlabel("Time [ns]")
        self.ax.set_ylabel("Voltage [V]")
        self.ax.legend()
        self.ax.grid(True)

        self.update_curve(self.ypoints)

    def show(self):
        plt.show(block=False)
        plt.pause(0.001)

    def update_curve(self, y:list):
        self.ypoints = np.array(y) / 4096 * self.vref
        self.curve_line.set_data(self.xpoints, self.ypoints)
        self.show()
