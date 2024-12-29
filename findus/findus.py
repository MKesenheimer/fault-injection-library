#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# This file is based on TAoFI-FaultLib which is released under the GPL3 license.
# Go to https://github.com/raelize/TAoFI-FaultLib/LICENSE for full license details.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

"""
Findus is a Python library to perform fault-injection attacks on embedded devices. It was developed for the PicoGlitcher, however, the ChipWhisperer Pro and the ChipWhisperer Husky is also supported.

This is the documentation of the findus module and all its classes.
"""

import sqlite3
import time
import ast
import serial
import sys
import chipwhisperer as cw
import datetime
from termcolor import colored
import os
import glob
from . import pyboard
from enum import Enum
from .GlitchState import ErrorType, WarningType, OKType, ExpectedType, SuccessType
try:
    from rd6006 import RD6006
    rd6006_available = True
except Exception as _:
    print("[-] Library RD6006 not installed. Functions to control the external power supply not available.")
    rd6006_available = False
from importlib.metadata import version
import random

class Database():
    """
    Database class managing access to the SQLite databases to store results from a glitching campaign.
    The parameter points stored in these databases are used to render an overview of the scanned parameter point via a web application.
    The web application and data analyzer can be run separately from the glitcher scripts by the following command:

        analyzer --directory databases

    Example usage:

        # import Database from findus
        from findus import Database
        ...
        database = Database(argv=argv)
        ...
        database.insert(experiment_id, delay, length, color, response)

    If `dbname` is not provided, a name will automatically generated based on `argv`.

    Methods:
        __init__: Default constructor.
        insert: Method to insert datapoints into the SQLite database.
        get_parameters_of_experiment: Get the parameters of a dataset by experiment_id.
        remove: Remove a parameter point from the database by experiment_id.
        cleanup: Remove all parameter points with a given color.
        get_number_of_experiments: Get the total number of performed experiments (number of datasets in the database).
        get_latest_experiment_id: Get the latest experiment_id.
        get_base_experiments_count: [Deprecated] Get the total number of performed experiments (number of datasets in the database).
        close: Close the connection to the database.
    """

    def __init__(self, argv: list[str], dbname: str = None, resume: bool = False, nostore: bool = False):
        """
        Default constructor of the Database class.

        Parameters:
            argv: Arguments that were supplied to the main-script. These arguments are stored as metadata when the database is instantiated.
            dbname: Name of the database to be generated.
            resume: Resume a previous run and write the results into the previously generated database
            nostore: Do not store the results in a database (can be used for debugging).
        """
        self.nostore = nostore
        if not os.path.isdir('databases'):
            os.mkdir("databases")

        if resume and dbname is None:
            list_of_files = glob.glob('databases/*.sqlite')
            latest_file = max(list_of_files, key=os.path.getctime)[10:]
            print(f"[+] Resuming previous database {latest_file}")
            self.dbname = latest_file
        elif dbname is None:
            script_name = os.path.basename(sys.argv[0])
            self.dbname = f"{script_name}_%s.sqlite" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        else:
            self.dbname = dbname

        self.con = sqlite3.connect("databases/" + self.dbname)
        self.cur = self.con.cursor()
        self.argv = argv
        if not resume and dbname is None:
            self.cur.execute("CREATE TABLE experiments(id integer, delay integer, length integer, color text, response blob)")
            self.cur.execute("CREATE TABLE metadata (stime_seconds integer, argv blob)")

        self.base_row_count = self.get_latest_experiment_id()
        if self.base_row_count is None:
            self.base_row_count = 0
        if resume or dbname is not None:
            print(f"[+] Number of experiments in previous database: {self.base_row_count}")

    def insert(self, experiment_id: int, delay: int, length: int, color: str, response: bytes):
        """
        Method to insert datapoints into the SQLite database.

        Parameters:
            experiment_id: ID of the experiment to insert into the database.
            delay: Time from trigger until the glitch is set (in nano seconds).
            length: Length of glitch (in nano seconds).
            color: Color with which the parameter point (delay, length) is to be displayed in the graph.
            response: Byte string of target response. 
        """
        if not self.nostore:
            if (experiment_id + self.base_row_count) == 0:
                s_argv = ' '.join(self.argv[1:])
                self.cur.execute("INSERT INTO metadata (stime_seconds,argv) VALUES (?,?)", [int(time.time()), s_argv])
            self.cur.execute("INSERT INTO experiments (id,delay,length,color,response) VALUES (?,?,?,?,?)", [experiment_id + self.base_row_count, delay, length, color, response])
            self.con.commit()

    def get_parameters_of_experiment(self, experiment_id: int) -> list:
        """
        Get the parameters of a dataset by experiment_id.

        Parameters:
            experiment_id: ID of the experiment to insert into the database.

        Returns:
            List of parameters.
        """
        self.cur.execute("SELECT * FROM experiments WHERE id = (?);", [experiment_id + self.base_row_count])
        self.con.commit()
        return next(self.cur, [None])

    def remove(self, experiment_id: int):
        """
        Remove a parameter point from the database by experiment_id.

        Parameters:
            experiment_id: ID of the experiment to insert into the database.
        """
        self.cur.execute("DELETE FROM experiments WHERE id = (?);", [experiment_id + self.base_row_count])
        self.con.commit()

    def cleanup(self, color):
        """
        Remove all parameter points with a given color.
        """
        self.cur.execute("DELETE FROM experiments WHERE color = (?);", [color])
        #self.cur.execute("DELETE FROM experiments WHERE length >= (?);", [color])
        self.con.commit()

    def get_number_of_experiments(self) -> int:
        """
        Get the total number of performed experiments (number of datasets in the database).

        Returns:
            Number of experiments performed so far in the current database.
        """
        self.cur.execute("SELECT count(id) FROM experiments")
        result = self.cur.fetchone()
        row_count = result[0]
        return row_count

    def get_latest_experiment_id(self) -> int:
        """
        Get the latest experiment_id.

        Returns:
            Experiment ID.
        """
        self.cur.execute("SELECT * FROM experiments WHERE id=(SELECT max(id) FROM experiments);")
        self.con.commit()
        return next(self.cur, [None])[0]

    def get_base_experiments_count(self) -> int:
        """
        [Deprecated] Get the total number of performed experiments (number of datasets in the database).

        Returns:
            Number of experiments performed so far in the current database.
        """
        return self.base_row_count

    def close(self):
        """
        Close the connection to the database.
        """
        self.con.close()

class Serial():
    r"""
    Class to manage serial connections more easily.
    Example usage:

        # import Serial from findus
        from findus import Serial
        ser = Serial(port="/dev/ttyUSB0")
        ser.write(b'\x7f')
        ...
        result = ser.read(3)

    Methods:
        __init__: Default constructor.
        write: Write data out via the serial interface.
        read: Read data from the serial interface.
        reset: Reset target via DTR pin and flush data lines.
        flush: Flush data buffers.
        flush_v2: Flush serial data buffers with timeout.
        close: Close serial connection.
    """
    def __init__(self, port:str = "/dev/ttyUSB0", baudrate:int = 115200, timeout:float = 0.1, bytesize:int = 8, parity:str = 'N', stopbits:int = 1):
        """
        __init__: Default constructor.

        Parameters:
            port: Port identifier of the serial connection.
            baudrate: Baudrate of the serial connection.
            timeout: Timeout after the serial connection stops listening.
            bytesize: Number of bytes per payload.
            parity: Even ('E') or Odd ('O') parity.
            stopbits: Number of stop bits.
        """
        self.ser = None
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.init()

    def init(self):
        """
        Initializes the serial connection. Can be called again, if the connection was closed previously.
        """
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout, bytesize=self.bytesize, parity=self.parity, stopbits=self.stopbits)

    def write(self, message: bytes) -> int:
        """
        Write the bytes data to the port. This should be of type `bytes` (or compatible such as `bytearray` or `memoryview`). Unicode strings must be encoded (e.g. `'hello'.encode('utf-8')`.

        Parameters:
            message: Data to send
        Returns:
            Number of bytes written.
        """
        return self.ser.write(message)

    def read(self, length: int) -> bytes:
        """
        Read `length` bytes from the serial port. If a timeout is set it may return fewer characters than requested. With no timeout it will block until the requested number of bytes is read.

        Parameters:
            length: Number of bytes to read.
        Returns:
            Bytes read from the port.
        """
        response = self.ser.read(length)
        return response
    
    def reset(self, debug:bool = False) -> bool:
        """
        Reset target via DTR pin and flush data lines. Can be used alternatively to the reset lines of the PicoGlitcher (or ChipWhisperer Husky, or ChipWhisperer Pro) to reset the target.

        Parameters:
            debug: If set to true, garbage on the serial interface is plotted to tty.
        """
        print("[+] Resetting target...")
        self.ser.dtr = True
        time.sleep(0.1)
        self.ser.dtr = False
        response = self.ser.read(4096)
        if debug:
            for line in response.splitlines():
                print('\t', line.decode())

    def flush(self):
        """
        Flush serial data buffers.
        """
        self.ser.reset_input_buffer()

    def flush_v2(self, timeout:float = 0.01):
        """
        Flush serial data buffers with timeout.

        Parameters:
            timeout: Timeout after the serial connection stops listening. Can be tweaked to make sure all data is flushed.
        """
        self.ser.timeout = timeout
        self.ser.read(8192)
        self.ser.timeout = self.timeout

    def close(self):
        """
        Close serial connection.
        """
        self.ser.close()

class MicroPythonScript():
    def __init__(self, port:str = '/dev/ttyACM1', debug:bool = False):
        self.port   = None
        self.pyb    = None
        self.debug = debug

    def init(self, port:str, micropy_script:str, debug:bool = False):
        self.port = port
        self.pyb = pyboard.Pyboard(self.port)
        self.pyb.enter_raw_repl()
        self.pyb.exec(f'import {micropy_script}')
        self.pyb.exec(f'mp = {micropy_script}.MicroPythonScript()')

# inherit functionality and overwrite some functions
class PicoGlitcherInterface(MicroPythonScript):
    def get_firmware_version(self):
        version_bytes = self.pyb.exec('mp.get_firmware_version()')
        decoded_str = version_bytes.decode('utf-8').strip()
        return ast.literal_eval(decoded_str)

    def set_trigger(self, mode:str, pin_trigger:str):
        self.pyb.exec(f'mp.set_trigger("{mode}", "{pin_trigger}")')

    def set_frequency(self, frequency:int):
        self.pyb.exec(f'mp.set_frequency({frequency})')

    def get_frequency(self):
        return self.pyb.exec('mp.get_frequency()')

    def set_baudrate(self, baud:int):
        self.pyb.exec(f'mp.set_baudrate({baud})')

    def set_number_of_bits(self, number_of_bits:int):
        self.pyb.exec(f'mp.set_number_of_bits({number_of_bits})')

    def set_pattern_match(self, pattern:int):
        self.pyb.exec(f'mp.set_pattern_match({pattern})')

    def power_cycle_target(self, power_cycle_time:float):
        self.pyb.exec(f'mp.power_cycle_target({power_cycle_time})')

    def arm(self, delay:int, length:int):
        self.pyb.exec(f'mp.arm({delay}, {length})')

    def arm_multiplexing(self, delay:int, mul_config:dict):
        self.pyb.exec(f'mp.arm_multiplexing({delay}, {mul_config})')

    def reset_target(self):
        self.pyb.exec('mp.reset_target()')

    def release_reset(self):
        self.pyb.exec('mp.release_reset()')

    def disable_vtarget(self):
        self.pyb.exec('mp.disable_vtarget()')

    def enable_vtarget(self):
        self.pyb.exec('mp.enable_vtarget()')

    def reset(self, reset_time:float):
        self.pyb.exec(f'mp.reset({reset_time})')

    def block(self, timeout:float):
        self.pyb.exec(f'mp.block({timeout})')

    def get_sm1_output(self) -> str:
        return self.pyb.exec('mp.get_sm1_output()')

    def set_lpglitch(self):
        self.pyb.exec('mp.set_lpglitch()')

    def set_hpglitch(self):
        self.pyb.exec('mp.set_hpglitch()')

    def set_multiplexing(self):
        self.pyb.exec('mp.set_multiplexing()')

    def set_dead_zone(self, dead_time:float, pin_condition:str):
        self.pyb.exec(f'mp.set_dead_zone({dead_time}, "{pin_condition}")')

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
            self.r.voltage = voltage
            self.r.enable = True
        except Exception as _:
            pass

    def enable_vtarget(self):
        """
        Enable voltage output.
        """
        self.r.enable = True

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

class Glitcher():
    """
    Glitcher template class. This class defines a common anchestor from which other glitcher modules should inherit from.

    Methods:
        __init__: Default constructor. Does nothing in this case.
        classify: Template method to classify an output state.
        colorize: Returns a colored string depending on a color identifier (G, Y, R, M, C, B).
        get_speed: Calculate and return the average speed of the glitching campaign (glitches per second).
    """
    def __init__(self):
        """
        Default constructor. Does nothing in this case.
        """
        pass

    def classify(self, state:type(Enum)) -> str:
        """
        Template method to classify an output state. Overload this class if you want to customize the targets response classification. Alternatively, use the built-in class `GlitchState` to characterize the targets responses. Remember to define certain response states depending on the possible responses. See class `BootloaderCom` for an example.

            from findus import PicoGlitcher
            from findus.BootloaderCom import BootloaderCom, GlitchState
            glitcher = PicoGlitcher()
            ...
            bootcom = BootloaderCom(port="/dev/ttyACM1")
            ...
            response = bootcom.init_bootloader()
            ...
            glitcher.classify(response)
        """
        if issubclass(type(state), ExpectedType):
            color = 'G'
        elif issubclass(type(state), SuccessType):
            color = 'R'
        elif issubclass(type(state), OKType):
            color = 'M'
        elif issubclass(type(state), ErrorType):
            color = 'Y'
        elif issubclass(type(state), WarningType):
            color = 'C'
        return color

    def colorize(self, s:str, color:str) -> str:
        """
        Returns a colorized string depending on a color identifier (G, Y, R, M, C, B).
        
        Parameters:
            s: The string you want to colorize.
            color: Color identifier, one of 'G', 'Y', 'R', 'M', 'C', 'B'.
        Returns:
            Returns the colorized string.
        """
        colors = {
            'G': 'green',
            'Y': 'yellow',
            'R': 'red',
            'M': 'magenta',
            'C': 'cyan',
            'B': 'blue',
        }
        return colored(s, colors[color])

    def get_speed(self, start_time:int, number_of_experiments:int) -> int:
        """
        Calculate and return the average speed of the glitching campaign (glitches per second).
        
        Parameters:
            start_time: Start time of the glitching campaign in seconds.
            number_of_experiments: Number of experiments carried out so far.
        Returns:
            Returns the average number of experiments per second.
        """
        elapsed_time = int(time.time()) - start_time
        if elapsed_time == 0:
            return 'NA'
        else:
            return number_of_experiments // elapsed_time

class PicoGlitcher(Glitcher):
    """
    Class giving access to the functions of the PicoGlitcher. Derived from Glitcher class.
    For an example, connect the PicoGlitcher as follows:

    - Remove any capacitors on your target device that could infere with the glitch.
    - Set the desired output voltage `VTARGET` with the micro switch.
    - Connect `VTARGET` with the voltage input of your target (`VCC`).
    - Connect the `GLITCH` output (either the SMA connector or the pin header) to an appropriate target pin, for example `VCC`.
    - Connect the `RESET` output with the target's reset input.
    - Connect the `RESET` line with the `TRIGGER` input.
    
    Code snippet:

        from findus import PicoGlitcher
        glitcher = PicoGlitcher()
        glitcher.init(port="/dev/ttyACM0", ext_power="/dev/ttyACM1", ext_power_voltage=3.3)
        # set up database, define delay and length
        ...
        # one shot glitching
        glitcher.arm(delay, length)
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
        arm: Arm the PicoGlitcher and wait for trigger condition.
        block: Block the main script until trigger condition is met. Times out.
        reset: Reset the target via the PicoGlitcher's `RESET` output.
        power_cycle_target: Power cycle the target via the PicoGlitcher `VTARGET` output.
        power_cycle_reset: Power cycle and reset the target via the PicoGlitcher `RESET` and `VTARGET` output. 
        reset_and_eat_it_all: Reset the target and flush the serial buffers.
        reset_wait: Reset the target and read from serial.
        set_lpglitch: Enable low-power MOSFET for glitch generation.
        set_hpglitch: Enable high-power MOSFET for glitch generation.
        rising_edge_trigger: Configure the PicoGlitcher to trigger on a rising edge on the `TRIGGER` line.
        uart_trigger: Configure the PicoGlitcher to trigger when a specific byte pattern is observed on the `TRIGGER` line.
        set_cpu_frequency: Set the CPU frequency of the Raspberry Pi Pico.
        get_cpu_frequency: Get the current CPU frequency of the Raspberry Pi Pico.
    """
    def __init__(self):
        """
        Default constructor. Does nothing in this case.
        """
        self.pico_glitcher = None

    def init(self, port:str, ext_power:str = None, ext_power_voltage:float = 3.3):
        """
        Default initialization procedure of the PicoGlitcher. Default configuration is:

        - Set the trigger input to rising-edge trigger on `TRIGGER` input and assume triggering when the reset is released.
        - Set a dead time that prohibits triggering within a certain time (trigger rejection). This is intended to exclude false trigger conditions.
        - Use the high-power crowbar MOSFET.

        Parameters:
            port: Port identifier of the PicoGlitcher.
            ext_power: Port identifier of the external power supply (RD6006). If None, target is assumed to be supplied by `VTARGET` of the PicoGlitcher.
            ext_power_voltage: Supply voltage of the external power supply. Must be used in combination with `ext_power`. You can not control the supply voltage `VTARGET` of the PicoGlitcher with this parameter.
        """
        self.pico_glitcher = PicoGlitcherInterface()
        self.pico_glitcher.init(port, 'mpGlitcher')

        # check compatibility
        try:
            pg_fw_version = self.pico_glitcher.get_firmware_version()
            fi_fw_version = list(map(int, version("findus").split('.')))
            print(f"Version of PicoGlitcher: {pg_fw_version}")
            print(f"Version of findus: {fi_fw_version}")
            if pg_fw_version != fi_fw_version:
                raise Exception("Version mismatch")
        except Exception as _:
            print("[-] Fatal error: Versions of findus and PicoGlitcher do not match.")
            print("[-] Update the PicoGlitcher firmware and findus software. See README.md.")
            sys.exit(-1)

        self.pico_glitcher.set_trigger("tio", "default")
        self.pico_glitcher.set_dead_zone(0, "default")
        self.pico_glitcher.set_frequency(200_000_000)
        self.pico_glitcher.set_hpglitch()
        if rd6006_available and ext_power is not None:
            self.pico_glitcher.disable_vtarget()
            self.power_supply = ExternalPowerSupply(port=ext_power)
            self.power_supply.set_voltage(ext_power_voltage)
            print(self.power_supply.status())
        else:
            self.pico_glitcher.enable_vtarget()
            self.power_supply = None

    def arm(self, delay:int, length:int):
        """
        Arm the PicoGlitcher and wait for the trigger condition. The trigger condition can either be when the reset on the target is released or when a certain pattern is observed in the serial communication.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            length: Length of the glitch in nano seconds. Expect a resolution of about 5 nano seconds.
        """
        self.pico_glitcher.arm(delay, length)

    def arm_multiplexing(self, delay:int, mul_config:dict):
        """
        Arm the PicoGlitcher and wait for the trigger condition. The trigger condition can either be when the reset on the target is released or when a certain pattern is observed in the serial communication.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 5 nano seconds.
            mul_config: <TODO>. Note: The default voltage when performing fault injection in multiplexing mode is 3.3V. This can not be changed by the variable `mul_config`. If you need to have a different default voltage, you may need to modify the `mpGlitcher.py` script.
        """
        self.pico_glitcher.arm_multiplexing(delay, mul_config)

    def block(self, timeout:float = 1.0):
        """
        Block until trigger condition is met. Raises an exception if times out.
        
        Parameters:
            timeout: Time after the block is released.
        """
        self.pico_glitcher.block(timeout)

    def get_sm1_output(self) -> str:
        return self.pico_glitcher.get_sm1_output()

    def reset(self, reset_time:float = 0.2):
        """
        Reset the target via the PicoGlitcher's `RESET` output.
        
        Parameters:
            reset_time: Time how long the target is held in reset.
        """
        self.pico_glitcher.reset(reset_time)

    def power_cycle_target(self, power_cycle_time:float = 0.2):
        """
        Power cycle the target via the PicoGlitcher `VTARGET` output.
        If available, target is power-cycled by the external power supply RD6006.
        
        Parameters:
            power_cycle_time: Time how long the power supply is cut. If `ext_power` is defined, the external power supply (RD6006) is cycled.
        """
        if self.power_supply is not None:
            self.power_supply.power_cycle_target(power_cycle_time)
        else:
            self.pico_glitcher.power_cycle_target(power_cycle_time)

    def power_cycle_reset(self, power_cycle_time:float = 0.2):
        """
        Power cycle and reset the target via the PicoGlitcher `VTARGET` and `RESET` output. Can also be used to define sharper trigger conditions via the `RESET` line.
        
        Parameters:
            power_cycle_time: Time how long the power supply is cut. If `ext_power` is defined, the external power supply is cycled.
        """
        if self.power_supply is not None:
            self.power_supply.disable_vtarget()
            self.pico_glitcher.reset_target()
            time.sleep(power_cycle_time)
            self.pico_glitcher.release_reset()
            self.power_supply.enable_vtarget()
        else:
            self.pico_glitcher.disable_vtarget()
            self.pico_glitcher.reset_target()
            time.sleep(power_cycle_time)
            self.pico_glitcher.release_reset()
            self.pico_glitcher.enable_vtarget()

    def reset_and_eat_it_all(self, target:serial.Serial, target_timeout:float = 0.3):
        """
        Reset the target via the PicoGlitcher's `RESET` output and flush the serial buffers.
        
        Parameters:
            target: Serial communication object (usually defined as `target = serial.Serial(...)`).
            target_timeout: Time-out of the serial communication. After this time, reading from the serial connection is canceled and it is assumed that there is no more garbage on the line.
        """
        self.pico_glitcher.reset_target()
        target.ser.timeout = target_timeout
        target.read(4096)
        target.ser.timeout = target.timeout
        self.pico_glitcher.release_reset()

    def reset_wait(self, target:serial.Serial, token:bytes, reset_time:float = 0.2, debug:bool = False) -> bytes:
        """
        Reset the target via the PicoGlitchers's `RESET` output and wait until the target responds (read from serial).

        Parameters:
            target: Serial communication object (usually defined as `target = serial.Serial(...)`).
            token: Expected response from target. Read from serial multiple times until target responds.
            reset_time:  Time how long the target is held under reset.
            debug: If `true`, more output is given.

        Returns:
            Returns the target's response.
        """
        self.pico_glitcher.reset_target()
        time.sleep(reset_time)
        self.pico_glitcher.release_reset()
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
        self.pico_glitcher.set_lpglitch()

    def set_hpglitch(self):
        """
        Enable the high-power crowbar MOSFET for glitch generation.
        
        The glitch output is an SMA-connected output line that is normally connected to a target's power rails. If this setting is enabled, a high-powered MOSFET shorts the power-rail to ground when the glitch module's output is active.
        """
        self.pico_glitcher.set_hpglitch()

    def set_multiplexing(self):
        """
        Enables the multiplexing mode of the PicoGlitcher version 2 to quickly switch between different voltage levels.
        """
        self.pico_glitcher.set_multiplexing()

    def rising_edge_trigger(self, pin_trigger:str = "default", dead_time:float = 0, pin_condition:str = "default"):
        """
        Configure the PicoGlitcher to trigger on a rising edge on the `TRIGGER` line.
        
        Parameters:
            pin_trigger: The trigger pin to use. Can be either "default" or "alt". For hardware version 2 options "ext1" or "ext2" can also be chosen.
            dead_time: Set a dead time that prohibits triggering within a certain time (trigger rejection). This is intended to exclude false trigger conditions. Can also be set to 0 to disable this feature.
            pin_condition: The rejection time is generated internally by measuring the state of the `power` or `reset` pin of the PicoGlitcher. If you want to trigger on the reset condition, set `pin_condition = 'reset'`, else if you want to trigger on the target power set `pin_condition = 'power'`. If `dead_time` is set to zero and `pin_condition = 'default'`, this parameter is ignored.
        """
        self.pico_glitcher.set_trigger("tio", pin_trigger)
        self.pico_glitcher.set_dead_zone(dead_time, pin_condition)

    def uart_trigger(self, pattern:int, baudrate:int = 115200, number_of_bits:int = 8, pin_trigger:str = "default"):
        """
        Configure the PicoGlitcher to trigger when a specific byte pattern is observed on the `TRIGGER` line.
        
        Parameters:
            pattern: Byte pattern that is transmitted on the serial lines to trigger on. For example `0x11`.
            baudrate: The baudrate of the serial communication.
            number_of_bits: The number of bits of the UART payload.
            pin_trigger: The trigger pin to use. Can be either "default" or "alt". For hardware version 2 options "ext1" or "ext2" can also be chosen.
        """
        self.pico_glitcher.set_trigger("uart", pin_trigger)
        self.pico_glitcher.set_baudrate(baudrate)
        self.pico_glitcher.set_number_of_bits(number_of_bits)
        self.pico_glitcher.set_pattern_match(pattern)

    def set_cpu_frequency(self, frequency:int = 200_000_000):
        """
        Set the CPU frequency of the Raspberry Pi Pico.
        
        Parameters:
            frequency: the CPU frequency.
        """
        self.pico_glitcher.set_frequency(frequency)

    def get_cpu_frequency(self) -> int:
        """
        Get the current CPU frequency of the Raspberry Pi Pico.
        
        Returns:
            Returns the CPU frequency.
        """
        return self.pico_glitcher.get_frequency()

class HuskyGlitcher(Glitcher):
    """
    Class giving access to the functions of the Chipwhisperer Husky. Derived from Glitcher class.
    Code snippet:

        from findus import HuskyGlitcher
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
        if rd6006_available and ext_power is not None:
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
            self.scope.io.tio3 = 'gpio_high'
            self.power_supply.enable_vtarget()
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

class ProGlitcher(Glitcher):
    """
    Class giving access to the functions of the Chipwhisperer Pro. Derived from Glitcher class.
    Code snippet:

        from findus import ProGlitcher
        glitcher = ProGlitcher()
        glitcher.init()
        # set up database, define delay and length
        ...
        # one shot glitching
        glitcher.arm(delay, length)
        # reset target for 0.01 seconds (the rising edge on reset line triggers the glitch)
        glitcher.reset(0.01)
        self.glitcher.block(timeout=1)

        # read the response from the device (for example UART, SWD, etc.)
        response = ...
        # classify the response and put into database
        color = glitcher.classify(response)
        database.insert(experiment_id, delay, length, color, response)

        # reset crowbar transistors
        self.glitcher.reset_glitch()

    Methods:
        __init__: Default constructor. Does nothing in this case.
        init: Default initialization procedure.
        arm: Arm the ChipWhisperer Pro and wait for trigger condition.
        capture: Captures trace. Scope must be armed before capturing.
        block: Block the main script until trigger condition is met. Times out.
        reset_glitch: Disables and enables crowbar MOSFETs. Waits `delay` seconds in between.
        reset: Reset the target via the ChipWhisperer Pro's `RESET` output.
        power_cycle_target: Power cycle the target via the ChipWhisperer Pro `VTARGET` output.
        power_cycle_reset: Power cycle and reset the target via the ChipWhisperer Pro `RESET` and `VTARGET` output.
        reset_and_eat_it_all: Reset the target and flush the serial buffers.
        reset_wait: Reset the target and read from serial.
        set_lpglitch: Enable low-power MOSFET for glitch generation.
        set_hpglitch: Enable high-power MOSFET for glitch generation.
        rising_edge_trigger: Configure the ChipWhisperer Pro to trigger on a rising edge on the `TRIGGER` line.
        uart_trigger: Configure the ChipWhisperer Pro to trigger when a specific byte pattern is observed on the `TRIGGER` line.
        disconnect: Disconnects the ChipWhisperer Pro.
        reconnect: Disconnects and reconnects the ChipWhisperer Pro.
        reconnect_with_uart: Disconnects and reconnects the ChipWhisperer Pro. The ChipWhisperer Pro is set up for UART glitching.
        __del__: Default deconstructor. Disconnects the ChipWhisperer Pro.
    """

    def __init__(self):
        """
        Default constructor. Does nothing in this case.
        """
        self.scope = None

    def init(self, ext_power:str = None, ext_power_voltage:float = 3.3):
        """
        Default initialization procedure of the ChipWhisperer Pro. Default configuration is:

        - Set the Pro's system clock to 100 MHz.
        - Set the trigger input to rising-edge trigger on `TIO4` pin.
        - Set reset out on `nrst` pin.
        - Set serial RX on `TIO1` and TX on `TIO2` pin (necessary for UART-trigger).
        - Use the high-power crowbar MOSFET.

        Parameters:
            ext_power: Port identifier of the external power supply (RD6006). If None, target is assumed to be supplied by the voltage supplies of the ChipWhisperer Pro UFO board.
            ext_power_voltage: Supply voltage of the external power supply. Must be used in combination with `ext_power`.
        """

        try:
            self.scope = cw.scope()
        except Exception as e:
            print("[-] No ChipWhisperer found. Exiting.")
            print(f"[-] Exception: {e}")
            sys.exit(1)

        self.scope.clock.adc_src            = "clkgen_x1"
        self.scope.clock.clkgen_freq        = 100e6
        self.scope.adc.basic_mode           = "rising_edge"
        self.scope.adc.samples              = 10000
        self.scope.adc.offset               = 0
        self.scope.io.tio1                  = 'high_z'  # UART RX
        self.scope.io.tio4                  = 'high_z'  # TRIGGER
        self.scope.trigger.triggers         = 'tio4'
        self.scope.io.hs2                   = "disabled"
        self.scope.io.glitch_hp             = True
        self.scope.io.glitch_lp             = False
        # Clock asynchronous glitching
        self.scope.glitch.clk_src           = 'clkgen'
        self.scope.glitch.output            = 'enable_only'
        self.scope.glitch.trigger_src       = 'ext_single'
        if rd6006_available and ext_power is not None:
            self.power_supply = ExternalPowerSupply(port=ext_power)
            self.power_supply.set_voltage(ext_power_voltage)
            print(self.power_supply.status())
        else:
            self.power_supply = None

    def arm(self, delay:int, length:int):
        """
        Arm the ChipWhisperer Pro and wait for the trigger condition. The trigger condition can either be trigger when the reset on the target is released or when a certain pattern is observed in the serial communication.

        Parameters:
            delay: Glitch is emitted after this time. Given in nano seconds. Expect a resolution of about 10 nano seconds.
            length: Length of the glitch in nano seconds. Expect a resolution of about 10 nano seconds.
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
        # TODO: set the timeout of scope.capture
        if self.scope.capture():
            raise Exception("Function execution timed out!")

    def reset_glitch(self, delay:float = 0.005):
        """
        Disables and enables crowbar MOSFETs. Waits `delay` seconds in between.
        Note: Up until now, only the high-power MOSFET is disabled and enabled again.

        Parameters:
            delay: Delay between disabling and re-enabling the crowbar MOSFETs.
        """
        # TODO: control hp and lp externally
        self.scope.io.glitch_hp = False
        self.scope.io.glitch_lp = False
        time.sleep(delay)
        self.scope.io.glitch_hp = True
        self.scope.io.glitch_lp = False

    def reset(self, reset_time:float = 0.2):
        """
        Reset the target via the ChipWhisperer Pro's `nrst` output.

        Parameters:
            reset_time: Time how long the target is held in reset.
        """
        self.scope.io.nrst = 'low'
        time.sleep(reset_time)
        self.scope.io.nrst = 'high_z'

    def power_cycle_target(self, power_cycle_time:float = 0.2):
        """
        Power cycle the target via the ChipWhisperer Pro's UFO board.
        If available, target is power-cycled by the external power supply RD6006.
        
        Parameters:
            power_cycle_time: Time how long the power supply is cut. If `ext_power` is defined, the external power supply (RD6006) is cycled.
        """
        if self.power_supply is not None:
            self.power_supply.power_cycle_target(power_cycle_time)
        else:
            self.scope.io.target_pwr = False
            time.sleep(power_cycle_time)
            self.scope.io.target_pwr = True

    def power_cycle_reset(self, power_cycle_time:float = 0.2):
        """
        Power cycle and reset the target via the ChipWhisperer Pro's UFO board and `nrst` output. Can also be used to define sharper trigger conditions via the `nrst` line.
        
        Parameters:
            power_cycle_time: Time how long the power supply is cut. If `ext_power` is defined, the external power supply is cycled.
        """
        if self.power_supply is not None:
            self.power_supply.disable_vtarget()
            self.scope.io.nrst = False
            time.sleep(power_cycle_time)
            self.scope.io.nrst = "high_z"
            self.power_supply.enable_vtarget()
        else:
            self.scope.io.target_pwr = False
            self.scope.io.nrst = False
            time.sleep(power_cycle_time)
            self.scope.io.nrst = "high_z"
            self.scope.io.target_pwr = True

    def reset_and_eat_it_all(self, target:serial.Serial, target_timeout:float = 0.3):
        """
        Reset the target via the ChipWhisperer Pro's `nrst` output and flush the serial buffers.

        Parameters:
            target: Serial communication object (usually defined as `target = serial.Serial(...)`).
            target_timeout: Time-out of the serial communication. After this time, reading from the serial connection is canceled and it is assumed that there is no more garbage on the line.
        """
        self.scope.io.nrst = 'low'
        target.ser.timeout = target_timeout
        target.read(4096)
        target.ser.timeout = target.timeout
        self.scope.io.nrst = 'high_z'

    def reset_wait(self, target:serial.Serial, token:bytes, reset_time:float = 0.2, debug:bool = False) -> str:
        """
        Reset the target via the ChipWhisperer Pro's `nrst` output and wait until the target responds (read from serial).

        Parameters:
            target: Serial communication object (usually defined as `target = serial.Serial(...)`).
            token: Expected response from target. Read from serial multiple times until target responds.
            reset_time:  Time how long the target is held under reset.
            debug: If `true`, more output is given.

        Returns:
            Returns the target's response.
        """
        self.scope.io.nrst = 'low'
        time.sleep(reset_time)
        self.scope.io.nrst = 'high_z'
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
        Configure the PicoGlitcher to trigger on a rising edge on the `TRIGGER` line (`tio4` pin).
        Note: `dead_time` and `pin` have no functions here (see `PicoGlitcher.rising_edge_trigger`).

        Parameters:
            pin_trigger: The trigger input pin to use. Default is tio4.
            dead_time: Unused.
            pin: Unused.
        """
        if pin_trigger == "default":
            self.scope.trigger.triggers = 'tio4'
            self.scope.io.tio4 = 'high_z'
        else:
            self.scope.trigger.triggers = pin_trigger
            # TODO: set self.scope.io.tiox based on pin_trigger

    def uart_trigger(self, pattern:int, baudrate:int = 115200, number_of_bits:int = 8, pin_trigger:str = "default"):
        """
        Configure the ChipWhisperer Pro to trigger when a specific byte pattern is observed on the RX line (`tio1` pin).
        Note: To comply with the STM32 bootloader, this is currently configured for even parity UART.

        Parameters:
            pattern: Byte pattern that is transmitted on the serial lines to trigger on. For example `0x11`.
            baudrate: The baudrate of the serial communication.
            number_of_bits: The number of bits of the UART payload (not implemented yet, default is 8).
            pin_trigger: The trigger pin to use.
        """
        # TODO: implement the number of bits.
        # UART trigger:
        # even parity problem
        # see: https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/
        CODE_READ = 0x80
        CODE_WRITE = 0xC0
        ADDR_DECODECFG = 57
        #ADDR_DECODEDATA = 58
        data = self.scope.decode_IO.oa.sendMessage(CODE_READ, ADDR_DECODECFG, Validate=False, maxResp=8)
        data[1] = data[1] | 0x01
        self.scope.decode_IO.oa.sendMessage(CODE_WRITE, ADDR_DECODECFG, data)
        if pin_trigger == "default":
            self.scope.trigger.triggers = 'tio1'
        else:
            self.scope.trigger.triggers = pin_trigger
        self.scope.trigger.module = 'DECODEIO'
        self.scope.decode_IO.rx_baud = baudrate
        self.scope.decode_IO.decode_type = 'USART'
        self.scope.decode_IO.trigger_pattern = [pattern]
        #self.scope.io.hs2 = "clkgen"

    def disconnect(self) -> bool:
        """
        Disconnects the ChipWhisperer Pro.

        Returns:
            True if the disconnection was successful, False otherwise.
        """
        if self.scope is not None:
            print("[+] Disconnecting ChipWhisperer Pro")
            #self.scope.io.glitch_hp = False
            #self.scope.io.glitch_lp = False
            return self.scope.dis()
        return False

    def reconnect(self, disconnect_wait:float = 0.5):
        """
        Disconnects and reconnects the ChipWhisperer Pro. The method `ProGlitcher.init()` for default initialization is called.

        Parameters:
            disconnect_wait: Time to wait during disconnects.
        """
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()

    def reconnect_with_uart(self, pattern:int, baudrate:int = 115200, number_of_bits:int = 8, disconnect_wait:float = 0.5, pin_trigger:str = "default"):
        """
        Disconnects and reconnects the ChipWhisperer Pro. The ChipWhisperer Pro is set up for UART glitching.

        Parameters:
            pattern: Byte pattern that is transmitted on the serial lines to trigger on. For example `0x11`.
            baudrate: The baudrate of the serial communication.
            number_of_bits: The number of bits of the UART payload (not implemented yet, default is 8).
            disconnect_wait: Time to wait during disconnects.
            pin_trigger: The trigger pin to use.
        """
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()
        self.uart_trigger(pattern, baudrate, number_of_bits, pin_trigger)

    def __del__(self):
        """
        Default deconstructor. Disconnects the ChipWhisperer Pro.
        """
        self.disconnect()

class Helper():
    """
    Helper class that provides useful functions.
    Example usage:
    
        from findus import Helper as helper
        filename = f"{helper.timestamp()}_memory_dump.bin"

    Methods:
        timestamp: Provides the current timestamp in a file-friendly format.
    """
    def timestamp() -> str:
        """
        Provides the current timestamp in a file-friendly format.
        
        Returns:
            Returns the current timestamp in the format %Y-%m-%d_%H-%M-%S.
        """
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

class Parameterspace():
    def __init__(self, parameter_boundaries:list[tuple[int, int]], parameter_divisions:list[int]):
        # TODO: sanity checks!
        self.parameter_boundaries = parameter_boundaries
        self.parameter_divisions = parameter_divisions
        self.cardinality = 1
        for num in self.parameter_divisions:
            self.cardinality *= num
        self.weights_per_bin = [0 for x in range( self.cardinality )]

    def get_cardinality(self):
        return self.cardinality

    def get_bin_assignment(self, *parameter:int) -> list[int]:
        fact = 1
        bina = 0
        for i in range(len(self.parameter_divisions)):
            division =  self.parameter_divisions[i]
            # xdelta = (xmax - xmin) / xdiv
            delta = (self.parameter_boundaries[i][1] - self.parameter_boundaries[i][0]) / division
            bin_number = int((parameter[i] - self.parameter_boundaries[i][0]) // delta)
            #print(f"par = {parameter[i]}, delta = {delta}, bina = {bin_number}")
            if i > 0:
                fact *= self.parameter_divisions[i - 1]
            bina += fact * bin_number
        return bina

    def add_experiment(self, weight:int, *parameter:int):
        for i in range(len(self.parameter_divisions)):
            if parameter[i] < self.parameter_boundaries[i][0] or parameter[i] >= self.parameter_boundaries[i][1]:
                print("[-] Error: parameter out of bounds. Skipping.")
                print(f"[-] Dimension: {i}, lower = {self.parameter_boundaries[i][0]}, upper = {self.parameter_boundaries[i][1]}, parameter = {parameter[i]}")
                return
        bina = self.get_bin_assignment(*parameter)
        self.weights_per_bin[bina] += weight

    def get_weights(self) -> list[int]:
        return self.weights_per_bin

    def get_bin_numbers_sorted_by_weights(self) -> list[int]:
        return sorted(range(len(self.weights_per_bin)), key=lambda i: self.weights_per_bin[i])

    def get_coordinates(self, bin_assignment:int) -> list[int]:
        bin_numbers = []
        reversed_parameter_divisions = list(reversed(self.parameter_divisions))
        fact = self.cardinality
        if bin_assignment > fact:
            print("[-] Error: bin number exceeds total number of bins.")
            return
        for div in reversed_parameter_divisions:
            c = (fact // div)
            b = int(bin_assignment // c)
            #print(f"bin_assignment = {bin_assignment}, fact = {fact}, div = {div}, (fact // div) = {c}, bin_number = {b}")
            bin_numbers.append(b)
            fact /= div
            bin_assignment -= b * c
        return list(reversed(bin_numbers))

    def get_boundaries_from_coordinates(self, coordinates:list[int]) -> list[tuple[int, int]]:
        boundaries = []
        for i in range(len(self.parameter_divisions)):
            division =  self.parameter_divisions[i]
            delta = (self.parameter_boundaries[i][1] - self.parameter_boundaries[i][0]) / division
            lower = self.parameter_boundaries[i][0] + delta * coordinates[i]
            upper = self.parameter_boundaries[i][0] + delta * (coordinates[i] + 1)
            tup = (int(lower), int(upper))
            boundaries.append(tup)
        return boundaries

    def get_boundaries(self, bin_assignment:int) -> list[tuple[int, int]]:
        bin_numbers = self.get_coordinates(bin_assignment)
        return self.get_boundaries_from_coordinates(bin_numbers)

class Individual():
    def __init__(self, parameters:list[int], max_age:int = 10):
        self.parameters = parameters
        self.health = 0
        self.max_age = max_age
        self.age = 0

    def set_genom(self, parameters:list[int]):
        self.parameters = parameters

    def get_genom(self) -> list[int]:
        return self.parameters

    def set_health(self, health:int):
        self.health = health

    def get_health(self) -> int:
        return self.health

    def get_age(self) -> int:
        return self.age

    def get_max_age(self) -> int:
        return self.max_age

    def increase_age(self):
        self.age += 1

class Population():
    def __init__(self, number_of_individuals:int, length_of_genom:int):
        if number_of_individuals < 10:
            print("[-] Error: Population too small.")
            sys.exit(-1)

        self.number_of_individuals = number_of_individuals
        self.length_of_genom = length_of_genom

        self.population = [None] * self.number_of_individuals
        for i in range(self.number_of_individuals):
            self.population[i] = self.generate_random_individual()

    def get_number_of_individuals(self) -> int:
        return self.number_of_individuals

    def get_length_of_genom(self) -> int:
        return self.length_of_genom

    def generate_random_individual(self) -> Individual:
        genom = [0] * self.length_of_genom
        for i in range(self.length_of_genom):
            genom[i] = random.uniform(0, 1)
        return Individual(genom)

    def get_individuals(self) -> list[Individual]:
        return self.population

    def set_individuals(self, individuals:list[Individual]):
        self.population = individuals

    def sort_by_health(self):
        self.population = sorted(self.population, key=lambda ind: ind.get_health())

    def update_health(self, health_function):
        for ind in self.population:
            ind.set_health(health_function(ind.get_genom()))
            #print(ind.get_health())

    def breed(self, i:int, j:int) -> Individual:
        geni = self.population[i].get_genom().copy()
        genj = self.population[j].get_genom().copy()
        for k in range(len(geni)):
            select = random.randint(0, 1)
            if select == 1:
                geni[k] = genj[k]
        return Individual(geni)

    def mutate(self, i:int) -> Individual:
        gene = random.randint(0, self.length_of_genom - 1)
        self.population[i].get_genom()[gene] = random.uniform(0, 1)

    def replace(self, i:int, individual:Individual):
        self.population[i] = individual

    def replace_with_random(self, i:int):
        self.population[i] = self.generate_random_individual()

    def kill_and_replace(self):
        for i in range(len(self.population)):
            if self.population[i].get_age() > self.population[i].get_max_age():
                self.population[i] = self.generate_random_individual()

    def increase_age_of_population(self):
        for i in range(len(self.population)):
            self.population[i].increase_age()

class GeneticAlgorithm:
    def __init__(self, parameterspace:Parameterspace, population:Population, health_malus_factor:float = 1):
        self.parameterspace = parameterspace
        self.population = population
        self.health_malus_factor = health_malus_factor

    def get_bins_from_genom(self, parameters:list[int]) -> list[int]:
        bins = [int(x * self.parameterspace.get_cardinality()) for x in parameters]
        return bins

    def health_function(self, parameters:list[int]) -> int:
        bins = self.get_bins_from_genom(parameters)
        """
        Calculates the health of a individual:

            health = Sum(weight_i) - factor * malus * Sum(weight_i)
            health = (1 - factor * malus) * Sum(weight_i)
        """
        # sum up the weights in each bin
        health = 0
        weights = self.parameterspace.get_weights()
        for b in bins:
            health += weights[b]

        # for every bin that occurs more than once, reduce health
        # (forces the algorithm to look into separate bins)
        # malus can maximal be the number of genoms (=bins),
        # therefore it is reasonable to choose health_malus_factor < (1 / number_of_bins)
        counts = {}
        for item in bins:
            counts[item] = counts.get(item, 0) + 1
        malus = 0
        for c in counts:
            if counts[c] > 1:
                malus += counts[c] - 1
        health -= (self.health_malus_factor * malus * health)

        return health

    def get_max_health(self) -> int:
        genom_length = self.population.get_length_of_genom()
        return max(self.parameterspace.get_weights()) * genom_length

    def step(self) -> list[Individual]:
        self.population.increase_age_of_population()
        self.population.update_health(self.health_function)
        self.population.sort_by_health()

        # Step 1: breeding
        number_of_individuals = self.population.get_number_of_individuals()
        child12 = self.population.breed(number_of_individuals - 1, number_of_individuals - 2)
        child21 = self.population.breed(number_of_individuals - 2, number_of_individuals - 1)
        child34 = self.population.breed(number_of_individuals - 3, number_of_individuals - 4)
        child43 = self.population.breed(number_of_individuals - 4, number_of_individuals - 3)
        # replace the individuals with bad health
        self.population.replace(0, child12)
        self.population.replace(1, child21)
        self.population.replace(2, child34)
        self.population.replace(3, child43)

        # Step 2: mutate
        self.population.mutate(0)
        self.population.mutate(2)

        # Step 3: replace weak individuals with random ones
        self.population.replace_with_random(4)
        self.population.replace_with_random(5)

        # Step 4: Kill old individuals
        self.population.kill_and_replace()

        self.population.update_health(self.health_function)
        self.population.sort_by_health()

        return self.population.get_individuals()

    def run(self, threshold:float) -> list[int]:
        maxhealth = self.get_max_health()
        while True:
            individuals = self.step()
            for ind in individuals:
                print(f"health of ind {ind}: {ind.get_health()}")
            print()
            if individuals[0].get_health() >= maxhealth * threshold:
                parameters = individuals[0].get_genom()
                return self.get_bins_from_genom(parameters)

    def get_population(self) -> Population:
        return self.population

    def get_parameterspace(self) -> Parameterspace:
        return self.parameterspace

class OptimizationController():
    def __init__(self, parameter_boundaries:list[tuple[int, int]], parameter_divisions:list[int], number_of_individuals:int = 10, length_of_genom:int = 20, malus_factor_for_equal_bins:float = 1):
        self.par = Parameterspace(parameter_boundaries, parameter_divisions)
        self.pop = Population(number_of_individuals, length_of_genom)
        # renorm the malus factor to the maximum number of genoms,
        # thus malus_factor_for_equal_bins can be chosen between 0 and 1.
        factor = malus_factor_for_equal_bins / length_of_genom
        self.opt = GeneticAlgorithm(self.par, self.pop, factor)
        self.i_current_individual = 0
        self.i_current_bin = 0
        self.number_of_individuals = self.pop.get_number_of_individuals()
        self.length_of_genom = self.pop.get_length_of_genom()

    def print_best_performing_bins(self):
        number_of_individuals = self.pop.get_number_of_individuals()
        ind0 = self.pop.get_individuals()[number_of_individuals - 1]
        print(f"[+] Individual health = {ind0.get_health()}, age = {ind0.get_age()}")
        print("[+] Best performing bins:")
        genom = ind0.get_genom()
        bins = self.opt.get_bins_from_genom(genom)
        boundaries = []
        for i in range(len(bins)):
            boundary = self.par.get_boundaries(bins[i])
            print(f"    bin = {bins[i]}: {boundary}")
            boundaries.append(boundary)

    def step(self) -> list[int]:
        individuals = self.pop.get_individuals()
        parameters = individuals[self.i_current_individual].get_genom()
        bins = self.opt.get_bins_from_genom(parameters)
        boundaries = self.par.get_boundaries(bins[self.i_current_bin])

        random_numbers = []
        for b in boundaries:
            random_numbers.append(random.randint(b[0], b[1]))

        # next bin
        self.i_current_bin += 1
        if self.i_current_bin >= self.length_of_genom:
            self.i_current_bin = 0
            # next individual
            self.i_current_individual += 1
            if self.i_current_individual >= self.number_of_individuals:
                self.i_current_individual = 0
                # next age step
                self.pop.set_individuals(self.opt.step())

        return random_numbers

    def add_experiment(self, weight:int, *parameter:int):
        self.par.add_experiment(weight, *parameter)