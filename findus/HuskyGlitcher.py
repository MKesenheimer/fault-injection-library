#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# This file is based on TAoFI-FaultLib which is released under the GPL3 license.
# Go to https://github.com/raelize/TAoFI-FaultLib/LICENSE for full license details.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

import sys
import time
import serial

from findus import Glitcher
try:
    import chipwhisperer as cw
except Exception as _:
    print("[-] Error: Library chipwhisperer not installed. Functions to interface the ChipWhisperer Pro and ChipWhisperer Husky not available.")
    print("    Install the chipwhisperer package with 'pip install chipwhisperer'")
    sys.exit(1)

class HuskyGlitcher(Glitcher):
    """
    Class giving access to the functions of the Chipwhisperer Husky. Derived from Glitcher class.
    Code snippet:

        from findus.HuskyGlitcher import HuskyGlitcher
        glitcher = HuskyGlitcher()
        glitcher.init(ext_power="/dev/ttyACM1", ext_power_voltage=3.3)
        # set up database, define delay and length
        ...
        # one shot glitching
        glitcher.arm(delay, length)
        self.glitcher.block(timeout=1)

        # reset target for 0.01 seconds (the rising edge on reset line triggers the glitch)
        glitcher.reset(0.01)
        # read the response from the device (for example UART, SWD, etc.)
        response = ...
        # classify the response and put into database
        color = glitcher.classify(response)
        database.insert(experiment_id, delay, length, color, response)

    Methods:
        __init__: Default constructor. Does nothing in this case.
        init: Default initialization procedure.
        arm: Arm the Husky and wait for trigger condition.
        capture: Captures trace. Scope must be armed before capturing.
        block: Block the main script until trigger condition is met. Times out.
        disable: Disables glitch and glitch outputs.
        enable: Enables glitch and glitch outputs.
        reset: Reset the target via the Husky's `RESET` output.
        power_cycle_target: Power cycle the target via the Husky `VTARGET` output.
        power_cycle_reset: Power cycle and reset the target via the Husky `RESET` and `VTARGET` output.
        reset_and_eat_it_all: Reset the target and flush the serial buffers.
        reset_wait: Reset the target and read from serial.
        set_lpglitch: Enable low-power MOSFET for glitch generation.
        set_hpglitch: Enable high-power MOSFET for glitch generation.
        rising_edge_trigger: Configure the Husky to trigger on a rising edge on the `TRIGGER` line.
        uart_trigger: Configure the Husky to trigger when a specific byte pattern is observed on the `TRIGGER` line.
        disconnect: Disconnects the Husky.
        reconnect: Disconnects and reconnects the Husky.
        reconnect_with_uart: Disconnects and reconnects the Husky. Husky is set up for UART glitching.
        __del__: Default deconstructor. Disconnects Husky.
    """

    def __init__(self):
        """
        Default constructor. Does nothing in this case.
        """
        self.scope = None

    def init(self, ext_power:str = None, ext_power_voltage:float = 3.3):
        """
        Default initialization procedure of the ChipWhisperer Husky. Default configuration is:

        - Set the Husky's system clock to 200 MHz.
        - Set the trigger input to rising-edge trigger on `TIO4` pin.
        - Set reset out on `TIO3` pin.
        - Set serial RX on `TIO1` and TX on `TIO2` pin (necessary for UART-trigger).
        - Use the high-power crowbar MOSFET.

        Parameters:
            ext_power: Port identifier of the external power supply (RD6006). If None, target is assumed to be supplied by a separate voltage source.
            ext_power_voltage: Supply voltage of the external power supply. Must be used in combination with `ext_power`.
        """
        self.scope = cw.scope()
        self.scope.clock.adc_mul             = 1
        self.scope.clock.clkgen_freq         = 200e6
        self.scope.clock.clkgen_src          = 'system'
        self.scope.adc.basic_mode            = "rising_edge"
        self.scope.io.tio1                   = 'serial_rx'
        self.scope.io.tio2                   = 'serial_tx'
        self.scope.io.tio3                   = 'gpio_low'    # RESET
        self.scope.io.tio4                   = 'high_z'      # TRIGGER in
        self.scope.trigger.triggers          = 'tio4'
        self.scope.io.hs2                    = "disabled"
        self.scope.io.glitch_trig_mcx        = 'glitch'
        self.scope.glitch.enabled            = True
        self.scope.glitch.clk_src            = 'pll'
        self.scope.io.glitch_hp              = True
        self.scope.io.glitch_lp              = False
        self.scope.glitch.output             = 'enable_only'
        self.scope.glitch.trigger_src        = 'ext_single'
        self.scope.glitch.num_glitches       = 1
        if ext_power is not None:
            from findus.ExternalPowerSupply import ExternalPowerSupply
            self.power_supply = ExternalPowerSupply(port=ext_power)
            self.power_supply.set_voltage(ext_power_voltage)
            print(self.power_supply.status())
        else:
            self.power_supply = None

    def arm(self, delay:int, length:int):
        """
        Arm the ChipWhisperer Husky and wait for the trigger condition. The trigger condition can either be trigger when the reset on the target is released or when a certain pattern is observed in the serial communication.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            length: Length of the glitch in nano seconds. Expect a resolution of about 5 nano seconds.
        """
        self.scope.glitch.ext_offset = delay // (int(1e9) // int(self.scope.clock.clkgen_freq))
        self.scope.glitch.repeat = length // (int(1e9) // int(self.scope.clock.clkgen_freq))
        self.scope.arm()

    def capture(self) -> bool:
        """
        Captures trace. Glitcher must be armed before capturing.
        Blocks until glitcher triggered (or times out), then disarms glitcher and copies data back.

        Returns:
            True if capture timed out, false if it didn't.
        Raises:
            IOError - Unknown failure.
        """
        return self.scope.capture()

    def block(self, timeout:float = 1):
        """
        Block until trigger condition is met. Raises an exception if times out.

        Parameters:
            timeout: Time after the block is released (not implemented yet).
        Raises:
            Timout exception.
        """
        # TODO: set the timeout of scope.capture.
        if self.scope.capture():
            raise Exception("Function execution timed out!")

    def disable(self):
        """
        Disables glitch and glitch outputs.
        """
        self.scope.glitch.enabled = False

    def enable(self):
        """
        Enables glitch and glitch outputs.
        """
        self.scope.glitch.enabled = True

    def reset(self, reset_time:float = 0.2):
        """
        Reset the target via the ChipWhisperer Husky's `RESET` output (`tio3` pin).

        Parameters:
            reset_time: Time how long the target is held in reset.
        """
        self.scope.io.tio3 = 'gpio_low'
        time.sleep(reset_time)
        self.scope.io.tio3 = 'gpio_high'

    def power_cycle_target(self, power_cycle_time:float = 0.2):
        """
        Power cycle the target via the external power supply (RD6006 or RK6006 if available). The parameter `ext_power` must be set in `HuskyGlitcher.init()`.

        Parameters:
            power_cycle_time: Time how long the power supply is cut.
        """
        if self.power_supply is not None:
            self.power_supply.power_cycle_target(power_cycle_time)
        else:
            print("[-] External power supply not available.")

    def power_cycle_reset(self, power_cycle_time:float = 0.2):
        """
        Power cycle the target via the external power supply (RD6006 or RK6006 if available), reset the device via the `RESET` line (`tio3` pin) simultaneously. Can also be used to define sharper trigger conditions via the `RESET` line.

        Parameters:
            power_cycle_time: Time how long the power supply is cut. If `ext_power` is defined, the external power supply is cycled.
        """
        if self.power_supply is not None:
            self.power_supply.disable_vtarget()
            self.scope.io.tio3 = 'gpio_low'
            time.sleep(power_cycle_time)
            self.power_supply.enable_vtarget()
            self.scope.io.tio3 = 'gpio_high'
        else:
            print("[-] External power supply not available.")

    def reset_and_eat_it_all(self, target:serial.Serial, target_timeout:float = 0.3):
        """
        Reset the target via the Husky's `RESET` output (`tio3` pin) and flush the serial buffers.

        Parameters:
            target: Serial communication object (usually defined as `target = serial.Serial(...)`).
            target_timeout: Time-out of the serial communication. After this time, reading from the serial connection is canceled and it is assumed that there is no more garbage on the line.
        """
        self.scope.io.tio3 = 'gpio_low'
        target.ser.timeout = target_timeout
        target.read(4096)
        target.ser.timeout = target.timeout
        self.scope.io.tio3 = 'gpio_high'

    def reset_wait(self, target:serial.Serial, token:bytes, reset_time:float = 0.2, debug:bool = False) -> bytes:
        """
        Reset the target via the Husky's `RESET` output (`tio3` pin) and wait until the target responds (read from serial).

        Parameters:
            target: Serial communication object (usually defined as `target = serial.Serial(...)`).
            token: Expected response from target. Read from serial multiple times until target responds.
            reset_time:  Time how long the target is held under reset.
            debug: If `true`, more output is given.

        Returns:
            Returns the target's response.
        """
        self.scope.io.tio3 = 'gpio_low'
        time.sleep(reset_time)
        self.scope.io.tio3 = 'gpio_high'
        response = target.read(4096)
        for _ in range(0, 5):
            if token in response:
                break
            response += target.read(4096)
        if debug:
            for line in response.splitlines():
                print('\t', line.decode())
        return response

    def set_lpglitch(self):
        """
        Enable the low-power crowbar MOSFET for glitch generation.

        The glitch output is an SMA-connected output line that is normally connected to a target's power rails. If this setting is enabled, a low-powered MOSFET shorts the power-rail to ground when the glitch module's output is active.
        """
        self.scope.io.glitch_hp = False
        self.scope.io.glitch_lp = True

    def set_hpglitch(self):
        """
        Enable the high-power crowbar MOSFET for glitch generation.

        The glitch output is an SMA-connected output line that is normally connected to a target's power rails. If this setting is enabled, a high-powered MOSFET shorts the power-rail to ground when the glitch module's output is active.
        """
        self.scope.io.glitch_hp = True
        self.scope.io.glitch_lp = False

    def rising_edge_trigger(self, pin_trigger:str = "default", dead_time:float = 0, pin:str = ""):
        """
        Configure the ChipWhisperer Pro to trigger on a rising edge on the `TRIGGER` line (`tio4` pin).
        Note: `dead_time` and `pin` have no functions here (see `PicoGlitcher.rising_edge_trigger`).

        Parameters:
            pin_trigger: The trigger input pin to use. Default is tio4.
            dead_time: Unused.
            pin: Unused.
        """
        self.scope.adc.basic_mode = "rising_edge"
        if pin_trigger == "default":
            self.scope.io.tio4 = 'high_z'
            self.scope.trigger.triggers = 'tio4'
        else:
            self.scope.trigger.triggers = pin_trigger
            # TODO: set self.scope.io.tiox based on pin_trigger

    def uart_trigger(self, pattern:int, baudrate:int = 115200, number_of_bits:int = 8, pin_trigger:str = "default"):
        """
        Configure the Husky to trigger when a specific byte pattern is observed on the RX line (`tio1` pin).

        Parameters:
            pattern: Byte pattern that is transmitted on the serial lines to trigger on. For example `0x11`.
            baudrate: The baudrate of the serial communication.
            number_of_bits: The number of bits of the UART payload (not implemented yet, default is 8).
            pin_trigger: The trigger pin to use.
        """
        # TODO: implement the number of bits.
        self.scope.io.hs2 = "clkgen"
        self.scope.trigger.module = 'UART'
        if pin_trigger == "default":
            self.scope.trigger.triggers = 'tio1'
        else:
            self.scope.trigger.triggers = pin_trigger
        self.scope.UARTTrigger.enabled = True
        self.scope.UARTTrigger.baud = baudrate
        self.scope.UARTTrigger.set_pattern_match(0, pattern)
        self.scope.UARTTrigger.trigger_source = 0

    def disconnect(self) -> bool:
        """
        Disconnects the Husky.

        Returns:
            True if the disconnection was successful, False otherwise.
        """
        if self.scope is not None:
            print("[+] Disconnecting ChipWhisperer Husky")
            #self.scope.io.glitch_hp = False
            #self.scope.io.glitch_lp = False
            return self.scope.dis()
        return False

    def reconnect(self, disconnect_wait:float = 0.5):
        """
        Disconnects and reconnects the Husky. The method `HuskyGlitcher.init()` for default initialization is called.

        Parameters:
            disconnect_wait: Time to wait during disconnects.
        """
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()

    def reconnect_with_uart(self, pattern:int, baudrate:int = 115200, number_of_bits:int = 8, disconnect_wait:float = 0.5, pin_trigger:str = "default"):
        """
        Disconnects and reconnects the Husky. Husky is set up for UART glitching.

        Parameters:
            pattern: Byte pattern that is transmitted on the serial lines to trigger on. For example `0x11`.
            baudrate: The baudrate of the serial communication.
            number_of_bits: The number of bits of the UART payload (not implemented yet, default is 8).
            disconnect_wait: Time to wait during disconnects.
            pin_trigger: The trigger pin to use. Can be either "default" or "alt". For hardware version 2 options "ext1" or "ext2" can also be chosen.
        """
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()
        self.uart_trigger(pattern, baudrate, number_of_bits, pin_trigger)

    def __del__(self):
        """
        Default deconstructor. Disconnects the Husky.
        """
        self.disconnect()
