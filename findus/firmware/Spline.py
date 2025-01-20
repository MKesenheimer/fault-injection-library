# Fast-Cubic-Spline-Python provides an implementation of 1D and 2D fast spline
# interpolation algorithm (Habermann and Kindermann 2007) in Python.
# Copyright (C) 2012, 2013 Joon H. Ro
# Modified and ported to Micropython by Matthias Kesenheimer, 2025.

# This file is part of Fast-Cubic-Spline-Python.

# Fast-Cubic-Spline-Python is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Fast-Cubic-Spline-Python is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Cubic spline interpolation using Habermann and Kindermann (2007)'s algorithm 
"""

try:
    import platform
    if platform.system() == 'Darwin' or platform.system() == 'Linux':
        from findus.firmware.decorators import micropython
except Exception as _:
    pass

class Spline():
    @staticmethod
    @micropython.native
    def calc_grid(a, b, n:int):
        n = int(n)
        h = 1
        if n > 0:
            h = (b - a) / n
        grid = [0] * int(n + 1)
        for i in range(n + 1):
            grid[i] = i * h + a
        return grid

    @staticmethod
    def interpolate_and_plot(xpoints:list[int], ypoints:list[int]) -> list[int]:
        from matplotlib import pyplot as plt
        a = xpoints[0]
        b = xpoints[-1]
        grid_hat = Spline.calc_grid(a, b, b - a)
        pulse = Spline.pchip_interpolate(xpoints, ypoints, grid_hat)
        plt.clf()
        line_approx = plt.plot(grid_hat, pulse, '-', label='pulse')
        plt.pause(0.001)
        plt.setp(line_approx, linewidth=2, linestyle='-')
        plt.legend()
        plt.show(block=False)
        return pulse

    @staticmethod
    @micropython.native
    def interpolate(x, y, grid_hat):
        n = len(x)
        h = [x[i+1] - x[i] for i in range(n-1)]

        # Solve for the coefficients of the spline:
        # Calculate the system of equations for second derivatives (M)
        alpha = [0] * (n-1)
        for i in range(1, n-1):
            if h[i] != 0 and h[i-1] != 0:
                alpha[i] = (3/h[i]) * (y[i+1] - y[i]) - (3/h[i-1]) * (y[i] - y[i-1])

        l = [1] + [0] * (n-1)
        mu = [0] * (n-1)
        z = [0] * n

        for i in range(1, n-1):
            l[i] = 2 * (x[i+1] - x[i-1]) - h[i-1] * mu[i-1]
            if l[i] != 0:
                mu[i] = h[i] / l[i]
                z[i] = (alpha[i] - h[i-1] * z[i-1]) / l[i]

        l[n-1] = 1
        z[n-1] = 0
        c = [0] * n
        b = [0] * (n-1)
        d = [0] * (n-1)
        a = [y[i] for i in range(n-1)]

        for j in range(n-2, -1, -1):
            c[j] = z[j] - mu[j] * c[j+1]
            if h[i] != 0 and h[j] != 0:
                b[j] = (y[j+1] - y[j]) / h[j] - h[j] * (c[j+1] + 2 * c[j]) / 3
                d[j] = (c[j+1] - c[j]) / (3 * h[j])

        # Interpolate at the query points
        def spline(x_val):
            for i in range(n-1):
                if x[i] <= x_val <= x[i+1]:
                    dx = x_val - x[i]
                    return a[i] + b[i] * dx + c[i] * dx**2 + d[i] * dx**3
            raise ValueError("Query point out of range")

        return [spline(q) for q in grid_hat]

    @staticmethod
    @micropython.native
    def pchip_interpolate(x, y, grid_hat):
        n = len(x)
        h = [x[i+1] - x[i] for i in range(n-1)]  # Interval lengths
        delta = [((y[i+1] - y[i]) / h[i]) if h[i] != 0 else 0 for i in range(n-1)]  # Slopes of secant lines

        # Compute the slopes (m_i)
        m = [0] * n
        m[0] = delta[0]  # Endpoint slope
        m[-1] = delta[-1]  # Endpoint slope

        for i in range(1, n-1):
            if delta[i-1] * delta[i] > 0:  # Monotonicity-preserving condition
                m[i] = 2 / (1/delta[i-1] + 1/delta[i])
            else:
                m[i] = 0  # Flat slope if signs differ

        # Interpolation function
        def hermite(x_val, i):
            t = 0
            if h[i] != 0:
                t = (x_val - x[i]) / h[i]
            h_i = h[i]
            t2 = t * t
            t3 = t2 * t

            h00 = (1 + 2*t) * (1 - t)**2
            h10 = t * (1 - t)**2
            h01 = t2 * (3 - 2*t)
            h11 = t3 - t2

            return (h00 * y[i] +
                    h10 * h_i * m[i] +
                    h01 * y[i+1] +
                    h11 * h_i * m[i+1])

        # Evaluate the query points
        def pchip_eval(x_val):
            for i in range(n-1):
                if x[i] <= x_val <= x[i+1]:
                    return hermite(x_val, i)
            raise ValueError("Query point out of range")

        return [pchip_eval(q) for q in grid_hat]

def pulse_test(i):
    xpoints = [0,   100, 200, 300, 400, 500, 515]
    ypoints = [3.0 + i, 2.0, 2.0, 2.0, 2.0, 0.0, 3.0]
    offset = 3.0
    points_per_volt = 1365
    points_per_ns = 0.1
    tpoints = [0] * len(xpoints)
    vpoints = [0] * len(xpoints)
    for i in range(len(xpoints)):
        tpoints[i] = int(xpoints[i] * points_per_ns)
        vpoints[i] = int((ypoints[i] - offset) * points_per_volt)
    pulse = Spline.interpolate_and_plot(tpoints, vpoints)
    print(pulse)

def pchip_test():
    x = [0, 1, 2, 3, 4, 5, 6]
    y = [0, 1, 0, 1, 1, 1, 1]
    a = x[0]
    b = x[-1]
    grid_hat = Spline.calc_grid(a, b, 50)

    fhat = Spline.pchip_interpolate(x, y, grid_hat)
    print(fhat)
    # plot
    from matplotlib import pyplot as plt
    line_approx = plt.plot(grid_hat, fhat, '-', label='interpolated')
    plt.setp(line_approx, linewidth=2, linestyle='-.')
    plt.legend()
    plt.show()

if __name__ == '__main__':
    #for i in range(200):
    #    pulse_test(i)
    #pulse_test(0)
    #input("Press enter to continue.")
    pchip_test()