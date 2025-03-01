#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import time
import sys
try:
    from rd6006 import RD6006
except Exception as _:
    print("[-] Error: Library RD6006 not installed. Functions to control the external power supply not available.")
    print("    Install the rd6006 package with 'pip install rd6006'")
    sys.exit(1)

class ExternalPowerSupply:
    """
    Wrapper class for the RD6006 voltage supply to align function names with the rest of the library.
    Example usage:
    
        from findus import ExternalPowerSupply
        power_supply = ExternalPowerSupply(port="/dev/ttyACM0")
        power_supply.set_voltage(ext_power_voltage)
        print(power_supply.status())
        power_supply.power_cycle_target(power_cycle_time)

    Methods:
        __init__: Default constructor.
        status: Get the status of the voltage supply.
        set_voltage: Set the voltage.
        enable_vtarget: Enable voltage output.
        disable_vtarget: Disable voltage output
        power_cycle_target: Power cycle the target (disables output, waits a certain time, enables voltage output again).
    """

    def __init__(self, port:str):
        """
        Default constructor.
        
        Parameters:
            port: Port identifier of the voltage supply.
        """
        self.port = port
        self.r = RD6006(self.port)

    def status(self) -> str:
        """
        Get the status of the voltage supply.

        Returns:
            Status message of the voltage supply.
        """
        return self.r.status()

    def set_voltage(self, voltage:float):
        """
        Set the voltage of the power supply.
        
        Parameters:
            voltage: Desired output voltage.
        """
        try:
            self.r.enable = False
            self.r.voltage = voltage
            self.r.enable = True
        except Exception as _:
            pass

    def enable_vtarget(self):
        """
        Enable voltage output.
        """
        try:
            self.r.enable = True
        except Exception as _:
            pass

    def disable_vtarget(self):
        """
        Disable voltage output.
        """
        self.r.enable = False

    def power_cycle_target(self, power_cycle_time:float = 0.2):
        """
        Power cycle the target (disables output, waits a certain time, enables voltage output again).
        
        Parameters:
            power_cycle_time: Time to wait between disabling and enabling the voltage output again.
        """
        self.r.enable = False
        time.sleep(power_cycle_time)
        self.r.enable = True
