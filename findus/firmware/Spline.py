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

import platform
if platform.system() == 'Darwin' or platform.system() == 'Linux':
    from decorators import micropython

class Spline():
    @staticmethod
    @micropython.native
    def _init_matrix(value, dimx, dimy):
        return [[value]*(dimy) for i in range(dimx)]

    @staticmethod
    @micropython.native
    def transpose(matrix):
        matrixT = Spline._init_matrix(0, len(matrix[0]), len(matrix))
        for i in range(len(matrix)):
            for j in range(len(matrix[0])):
                matrixT[j][i] = matrix[i][j]
        return matrixT

    @staticmethod
    @micropython.native
    def Pi(t:float):
        abs_t = abs(t)
        if abs_t <= 1:
            return (4 - 6 * abs_t**2 + 3 * abs_t **3)
        elif abs_t <= 2:
            return ((2 - abs_t)**3)
        else:
            return (0)

    @staticmethod
    @micropython.native
    def u(x:float, k:int, a:float, h:float):
        return (Spline.Pi((x - a)/h - (k - 2)))

    @staticmethod
    @micropython.native
    def interpolate(x:float, a:float, b:float, c:list[float]):
        """
        Return interpolated function value at x.

        Parameters
            x: The value where the function will be approximated at
            a: Lower bound of the grid
            b: Upper bound of the grid
            c: Coefficients of spline

        Returns
            out: Approximated function value at x
        """
        return(Spline._interpolate(x, a, b, c))

    @staticmethod
    @micropython.native
    def _interpolate(x:float, a:float, b:float, c:list[float]):
        n = len(c) - 3
        h = (b - a) / n
        ll = int(((x - a) // h) + 1)
        m = int(min(ll + 3, n + 3))
        s = 0
        for i1 in range(ll, m + 1):
            s += c[i1 - 1] * Spline.u(x, i1, a, h)
        return s

    @staticmethod
    @micropython.native
    def interpolate_2d(x:float, y:float, a1:float, b1:float, a2:float, b2:float, c:list[list[float]]):
        """
        Return interpolated function value at x

        Parameters:
            x, y: The values where the function will be approximated at
            a1, b1: Lower and upper bounds of the grid for x
            a2, b2: Lower and upper bounds of the grid for y
            c: Coefficients of spline

        Returns:
            out: Approximated function value at (x, y)
        """
        return (Spline._interpolate_2d(x, y, a1, b1, a2, b2, c))

    @staticmethod
    @micropython.native
    def _interpolate_2d(x:float, y:float, a1:float, b1:float, a2:float, b2:float, c:list[list[float]]):
        n1 = len(c) - 3
        n2 = len(c[0]) - 3
        h1 = (b1 - a1)/n1
        h2 = (b2 - a2)/n2
        l1 = int(((x - a1)//h1) + 1)
        l2 = int(((y - a2)//h2) + 1)
        m1 = int((min(l1 + 3, n1 + 3)))
        m2 = int((min(l2 + 3, n2 + 3)))
        s = 0
        for i1 in range(l1, m1 + 1):
            u_x = Spline.u(x, i1, a1, h1)
            for i2 in range(l2, m2 + 1):
                u_y = Spline.u(y, i2, a2, h2)
                s += c[i1 - 1][i2 - 1] * u_x * u_y
        return s

    @staticmethod
    @micropython.native
    def _solve_banded(Aa, va, up, down):
        # Copy the inputs and determine the size of the system
        A = Aa.copy()
        v = va.copy()
        N = len(v)

        # Gaussian elimination
        for m in range(N):
            # Normalization factor
            div = A[up][m]

            # Update the vector first
            v[m] /= div
            for k in range(1, down + 1):
                if m + k < N:
                    v[m + k] -= A[up+k][m] * v[m]

            # Now normalize the pivot row of A and subtract from lower ones
            for i in range(up):
                j = m + up - i
                if j < N:
                    A[i][j] /= div
                    for k in range(1, down + 1):
                        A[i + k][j] -= A[up + k][m] * A[i][j]

        # Backsubstitution
        for m in range(N-2,-1,-1):
            for i in range(up):
                j = m + up - i
                if j < N:
                    v[m] -= A[i][j] * v[j]
        return v

    @staticmethod
    @micropython.native
    def cal_coefs(a, b, y, alpha=0, beta=0) -> list[float]:
        """
        Return spline coefficients 

        Parameters:
            a: lower bound of the grid.
            b: upper bound of the grid.
            y: actual function value at grid points.
            c: matrix to be written
            alpha: Second-order derivative at a. Default is 0.
            beta: Second-order derivative at b. Default is 0.

        Returns:
         out: Array of coefficients.
        """
        n = len(y) - 1
        h = (b - a) / n
        c = [0] * (n + 3)

        c[1] = 1/6 * (y[0] - (alpha * h**2)/6)
        c[n + 1] = 1/6 * (y[n] - (beta * h**2)/6)

        # ab matrix here is just compressed banded matrix
        ab = Spline._init_matrix(1, 3, n - 1)
        ab[0][0] = 0
        for i in range(len(ab[1])):
            ab[1][i] = 4
        ab[-1][-1] = 0

        B = y[1:-1].copy()
        B[0]  -= c[1]
        B[-1] -= c[n + 1]
        c[2:-2] = Spline._solve_banded(ab, B, 1, 1)

        c[0] = alpha * h**2/6 + 2 * c[1] - c[2]
        c[-1] = beta * h**2/6 + 2 * c[-2] - c[-3]
        return c

    @staticmethod
    @micropython.native
    def calc_grid(a, b, n):
        h = 1
        if n > 0:
            h = (b - a) / n
        grid = [0] * int(n + 1)
        for i in range(n + 1):
            grid[i] = i * h + a
        return grid

    @staticmethod
    @micropython.native
    def interpolate_points(xpoints:list[int], ypoints:list[int]) -> list[int]:
        a = xpoints[0]
        b = xpoints[-1]
        c = Spline.cal_coefs(a, b, ypoints)
        grid_hat = Spline.calc_grid(a, b, b - a) # grid with step one
        fhat = list([Spline.interpolate(x, a, b, c) for x in grid_hat])
        return fhat

    @staticmethod
    def interpolate_and_plot(xpoints:list[int], ypoints:list[int]) -> list[int]:
        pulse = Spline.interpolate_points(xpoints, ypoints)
        from matplotlib import pyplot as plt
        a = xpoints[0]
        b = xpoints[-1]
        grid_hat = Spline.calc_grid(a, b, b - a)
        plt.clf()
        line_approx = plt.plot(grid_hat, pulse, '-', label='pulse')
        plt.pause(0.001)
        plt.setp(line_approx, linewidth=2, linestyle='-')
        plt.legend()
        plt.show(block=False)
        return pulse


def one_dimensional():
    # 1D interpolation
    # trunk-ignore(ruff/E731)
    f = lambda x: x**2

    a = -1
    b = 1
    grid = Spline.calc_grid(a, b, 10)

    y = list(map(f, grid))
    c = Spline.cal_coefs(a, b, y)

    grid_hat = Spline.calc_grid(a, b, 100)
    fhat = list([Spline.interpolate(x, a, b, c) for x in grid_hat])

    from matplotlib import pyplot as plt
    line_actual = plt.plot(grid_hat, list(map(f, grid_hat)), label='actual')
    line_approx = plt.plot(grid_hat, fhat, '-.', label='interpolated')
    plt.setp(line_actual, linewidth=1, linestyle='--')
    plt.setp(line_approx, linewidth=2, linestyle='-.')
    plt.legend()
    plt.show()

def interpolation_test():
    xpoints = [0, 10, 20]
    ypoints = [1, 0, 1]
    fhat = Spline.interpolate_points(xpoints, ypoints)
    print(fhat)

    # plot
    from matplotlib import pyplot as plt
    a = xpoints[0]
    b = xpoints[-1]
    grid_hat = Spline.calc_grid(a, b, b - a)
    line_approx = plt.plot(grid_hat, fhat, '-.', label='interpolated')
    plt.setp(line_approx, linewidth=2, linestyle='-.')
    plt.legend()
    plt.show()

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

if __name__ == '__main__':
    #one_dimensional()
    #interpolation_test()
    #for i in range(200):
    #    pulse_test(i)
    pulse_test(0)
    input("Press enter to continue.")