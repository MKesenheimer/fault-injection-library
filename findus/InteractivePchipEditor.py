#!/usr/bin/env python3
# Copyright (C) 2025 Bedri Zija - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from scipy.interpolate import PchipInterpolator
try:
    import tkinter as tk
    from tkinter.scrolledtext import ScrolledText
except Exception as _:
    pass

class InteractivePchipEditor:
    def __init__(self):
        self.xpoints = [0, 48, 101, 139, 185, 229, 263, 399]
        self.ypoints = [3.0, 3.0, 1.5, 1.5, 0.0, 1.9, 2.5, 3.0]
        #self.xpoints = [0, 50, 75, 100, 139, 185, 229, 263, 400, 500, 600]
        #self.ypoints = [3.0, 3.0, 2.0, 1.5, 1.5, 0.0, 1.9, 2.5, 3.0, 3.0, 3.0]

        self.fig, self.ax = plt.subplots()
        plt.subplots_adjust(bottom=0.3)
        self.selected_point = None

        self.curve_line, = self.ax.plot([], [], label="PCHIP Curve", color="blue")
        self.point_scatter = self.ax.scatter(self.xpoints, self.ypoints, color="red", s=50, label="Control Points", picker=True)

        self.ax.set_xlim(-50, 1000)
        self.ax.set_ylim(-0.5, 3.5)
        self.ax.set_xlabel("Time (ns)")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.legend()
        self.ax.grid(True)

        save_ax = plt.axes([0.8, 0.05, 0.1, 0.075])
        self.save_button = Button(save_ax, 'Save')
        self.save_button.on_clicked(self.save_points)

        self.update_curve()
        self.cid_click = self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.cid_release = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)

    def create_text_window(self, output):
        self.root = tk.Tk()
        self.root.title("Saved Points")
        self.text_output = ScrolledText(self.root, wrap=tk.WORD, width=40, height=10, font=("Courier", 10))
        self.text_output.pack(fill=tk.BOTH, expand=True)
        self.text_output.insert(tk.END, output)
        self.text_output.configure(state='normal')  # Enable copying
        self.root.attributes("-topmost", True)  # Keep window on top
        self.root.mainloop()

    def update_curve(self):
        interpolator = PchipInterpolator(self.xpoints, self.ypoints)
        x_smooth = np.linspace(min(self.xpoints), max(self.xpoints), 500)
        y_smooth = interpolator(x_smooth)
        self.curve_line.set_data(x_smooth, y_smooth)
        self.point_scatter.set_offsets(np.c_[self.xpoints, self.ypoints])
        self.fig.canvas.draw_idle()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        contains, index = self.point_scatter.contains(event)
        if contains:
            self.selected_point = index["ind"][0]

    def on_release(self, event):
        self.selected_point = None

    def on_motion(self, event):
        if self.selected_point is None or event.inaxes != self.ax:
            return

        new_x = np.clip(event.xdata, 0, 1000)
        new_y = np.clip(event.ydata, 0, 3.3)
        self.xpoints[self.selected_point] = new_x
        self.ypoints[self.selected_point] = new_y

        self.xpoints = sorted(self.xpoints)  # Keep xpoints sorted
        self.update_curve()

    def save_points(self, event):
        xpoints_str = ", ".join(f"{x:.0f}" for x in self.xpoints)
        ypoints_str = ", ".join(f"{y:.1f}" for y in self.ypoints)
        output = f"xpoints = [{xpoints_str}]\nypoints = [{ypoints_str}]"
        try:
            self.create_text_window(output)
        except Exception as _:
            print(output)

    def get_points(self):
        return [float(x) for x in self.xpoints], [float(x) for x in self.ypoints]

    def show(self, block=True):
        plt.show(block=block)
        plt.pause(0.001)

def main():
    editor = InteractivePchipEditor()
    editor.show()
    editor.get_points()

if __name__ == "__main__":
    main()
