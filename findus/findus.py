#!/usr/bin/env python3
# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# This file is based on TAoFI-FaultLib which is released under the GPL3 license.
# Go to https://github.com/raelize/TAoFI-FaultLib/LICENSE for full license details.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: m.kesenheimer@gmx.net.

"""
findus - Python library to perform fault-injection attacks on embedded devices

This is the documentation of the findus module and all its classes.
"""

import sqlite3
import time
import serial
import sys
import chipwhisperer as cw
import datetime
from termcolor import colored
import os
import glob
from . import pyboard
from .GlitchState import ErrorType, WarningType, OKType, ExpectedType, SuccessType
try:
    from rd6006 import RD6006
    rd6006_available = True
except Exception as _:
    print("[-] Library RD6006 not installed. Functions to control the external power supply not available.")
    rd6006_available = False

class Database():
    """
    Database class managing access to the SQLite databases to store results from a glitching campaign.
    The parameter points stored in these databases are used to render an overview of the scanned parameter point via a web application.
    The web application and data analyzer can be run separately from the glitcher scripts by the following command:

        python ../analyzer/taofi-analyzer --directory databases

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
    def __init__(self, port:str = "/dev/ttyUSB0", baudrate:int = 115200, timeout:float = 0.1, bytesize:int = 8, parity:str = 'E', stopbits:int = 1):
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
    def __init__(self, port='/dev/ttyACM1', debug=False):
        self.port   = None
        self.pyb    = None
        self.debug = debug

    def init(self, port, micropy_script, debug=False):
        self.port = port
        self.pyb = pyboard.Pyboard(self.port)
        self.pyb.enter_raw_repl()
        self.pyb.exec(f'import {micropy_script}')
        self.pyb.exec(f'mp = {micropy_script}.MicroPythonScript()')


# inherit functionality and overwrite some functions
class PicoGlitcherInterface(MicroPythonScript):
    def set_trigger(self, trigger):
        self.pyb.exec(f'mp.set_trigger("{trigger}")')

    def set_frequency(self, frequency):
        self.pyb.exec(f'mp.set_frequency({frequency})')

    def set_baudrate(self, baud):
        self.pyb.exec(f'mp.set_baudrate({baud})')

    def set_pattern_match(self, pattern):
        self.pyb.exec(f'mp.set_pattern_match({pattern})')

    def power_cycle_target(self, power_cycle_time):
        self.pyb.exec(f'mp.power_cycle_target({power_cycle_time})')

    def arm(self, delay, length):
        self.pyb.exec(f'mp.arm({delay}, {length})')

    def reset_target(self):
        self.pyb.exec('mp.reset_target()')

    def release_reset(self):
        self.pyb.exec('mp.release_reset()')

    def disable_vtarget(self):
        self.pyb.exec('mp.disable_vtarget()')

    def enable_vtarget(self):
        self.pyb.exec('mp.enable_vtarget()')

    def reset(self, reset_time):
        self.pyb.exec(f'mp.reset({reset_time})')

    def block(self, timeout):
        return self.pyb.exec(f'mp.block({timeout})')

    def get_sm2_output(self):
        return self.pyb.exec('mp.get_sm2_output()')

    def set_lpglitch(self):
        self.pyb.exec('mp.set_lpglitch()')

    def set_hpglitch(self):
        self.pyb.exec('mp.set_hpglitch()')

    def set_dead_zone(self, dead_time, pin):
        self.pyb.exec(f'mp.set_dead_zone({dead_time}, "{pin}")')

class ExternalPowerSupply:
    def __init__(self, port):
        self.port = port
        self.r = RD6006(self.port)

    def status(self):
        return self.r.status()

    def set_voltage(self, voltage):
        self.r.voltage = voltage
        self.r.enable = True

    def enable_vtarget(self):
        self.r.enable = True

    def disable_vtarget(self):
        self.r.enable = False

    def power_cycle_target(self, power_cycle_time=0.2):
        self.r.enable = False
        time.sleep(power_cycle_time)
        self.r.enable = True


class Glitcher():
    def __init__(self):
        pass

    def classify(self, state):
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

    def colorize(self, s, color):
        colors = {
            'G': 'green',
            'Y': 'yellow',
            'R': 'red',
            'M': 'magenta',
            'C': 'cyan',
            'B': 'blue',
        }
        return colored(s, colors[color])

    def get_speed(self, start_time, number_of_experiments):
        elapsed_time = int(time.time()) - start_time
        if elapsed_time == 0:
            return 'NA'
        else:
            return number_of_experiments // elapsed_time


class PicoGlitcher(Glitcher):
    def __init__(self):
        self.pico_glitcher = None

    def init(self, port, ext_power=None, ext_power_voltage=3.3):
        self.pico_glitcher = PicoGlitcherInterface()
        self.pico_glitcher.init(port, 'mpGlitcher')
        self.pico_glitcher.set_trigger("tio")
        self.pico_glitcher.set_dead_zone(0.03, "power")
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

    def arm(self, delay, length):
        """
        Arm the PicoGlitcher.
        """
        self.pico_glitcher.arm(delay, length)

    def block(self, timeout=1):
        self.pico_glitcher.block(timeout)

    def get_sm2_output(self):
        return self.pico_glitcher.get_sm2_output()

    def reset(self, reset_time=0.2):
        self.pico_glitcher.reset(reset_time)

    def power_cycle_target(self, power_cycle_time=0.2):
        if self.power_supply is not None:
            self.power_supply.power_cycle_target(power_cycle_time)
        else:
            self.pico_glitcher.power_cycle_target(power_cycle_time)

    def power_cycle_reset(self, power_cycle_time=0.2):
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

    def reset_and_eat_it_all(self, target, target_timeout=0.3):
        self.pico_glitcher.reset_target()
        target.ser.timeout = target_timeout
        target.read(4096)
        target.ser.timeout = target.timeout
        self.pico_glitcher.release_reset()

    def reset_wait(self, target, token, reset_time=0.2, debug=False):
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

    def set_lpglitch(self):
        self.pico_glitcher.set_lpglitch()

    def set_hpglitch(self):
        self.pico_glitcher.set_hpglitch()

    def rising_edge_trigger(self, dead_time, pin):
        self.pico_glitcher.set_trigger("tio")
        self.pico_glitcher.set_dead_zone(dead_time, pin)

    def uart_trigger(self, pattern):
        self.pico_glitcher.set_trigger("uart")
        self.pico_glitcher.set_baudrate(115200)
        self.pico_glitcher.set_pattern_match(pattern)


class HuskyGlitcher(Glitcher):
    def __init__(self):
        self.scope = None

    def init(self, ext_power=None, ext_power_voltage=3.3):
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

    def arm(self, delay, length):
        self.scope.glitch.ext_offset = delay // (int(1e9) // int(self.scope.clock.clkgen_freq))
        self.scope.glitch.repeat = length // (int(1e9) // int(self.scope.clock.clkgen_freq))
        self.scope.arm()

    def capture(self):
        self.scope.capture()

    def block(self, timeout=1):
        # TODO: set the timeout of scope.capture
        # blocks until scope triggered (or times out),
        # then disarms scope and copies data back.
        if self.scope.capture():
            raise Exception("Function execution timed out!")

    def disable(self):
        self.scope.glitch.enabled = False

    def enable(self):
        self.scope.glitch.enabled = True

    def reset(self, reset_time=0.2):
        self.scope.io.tio3 = 'gpio_low'
        time.sleep(reset_time)
        self.scope.io.tio3 = 'gpio_high'

    def reset_and_eat_it_all(self, target, target_timeout=0.3):
        self.scope.io.tio3 = 'gpio_low'
        target.ser.timeout = target_timeout
        target.read(4096)
        target.ser.timeout = target.timeout
        self.scope.io.tio3 = 'gpio_high'

    def reset_wait(self, target, token, reset_time=0.2, debug=False):
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

    husky_reset_wait = reset_wait

    def power_cycle_target(self, power_cycle_time=0.2):
        if self.power_supply is not None:
            self.power_supply.power_cycle_target(power_cycle_time)
        else:
            print("[-] External power supply not available.")

    def power_cycle_reset(self, power_cycle_time=0.2):
        if self.power_supply is not None:
            self.power_supply.disable_vtarget()
            self.scope.io.tio3 = 'gpio_low'
            time.sleep(power_cycle_time)
            self.scope.io.tio3 = 'gpio_high'
            self.power_supply.enable_vtarget()
        else:
            print("[-] External power supply not available.")

    def set_lpglitch(self):
        self.scope.io.glitch_hp = False
        self.scope.io.glitch_lp = True

    def set_hpglitch(self):
        self.scope.io.glitch_hp = True
        self.scope.io.glitch_lp = False

    def rising_edge_trigger(self, dead_time, pin):
        # Note: dead_time and pin have no functions here (see PicoGlitcher.rising_edge_trigger)
        self.scope.adc.basic_mode = "rising_edge"
        self.scope.io.tio4 = 'high_z'
        self.scope.trigger.triggers = 'tio4'

    def uart_trigger(self, pattern):
        self.scope.io.hs2 = "clkgen"
        self.scope.trigger.module = 'UART'
        self.scope.trigger.triggers = 'tio1'
        self.scope.UARTTrigger.enabled = True
        self.scope.UARTTrigger.baud = 115200
        self.scope.UARTTrigger.set_pattern_match(0, pattern)
        self.scope.UARTTrigger.trigger_source = 0

    def disconnect(self):
        if self.scope is not None:
            print("[+] Disconnecting ChipWhisperer Husky")
            #self.scope.io.glitch_hp = False
            #self.scope.io.glitch_lp = False
            self.scope.dis()

    def reconnect(self, disconnect_wait=0.5):
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()

    def reconnect_with_uart(self, pattern, disconnect_wait=0.5):
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()
        self.uart_trigger(pattern)

    def __del__(self):
        self.disconnect()


class ProGlitcher(Glitcher):
    def __init__(self):
        self.scope = None

    def init(self, ext_power=None, ext_power_voltage=3.3):
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
        self.scope.io.tio1                  = 'high_z'
        self.scope.io.tio4                  = 'high_z'
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

    def reset_glitch(self, delay=0.005):
        # TODO: control hp and lp externally
        self.scope.io.glitch_hp = False
        self.scope.io.glitch_lp = False
        time.sleep(delay)
        self.scope.io.glitch_hp = True
        self.scope.io.glitch_lp = False

    def arm(self, delay, length):
        self.scope.glitch.ext_offset = delay // (int(1e9) // int(self.scope.clock.clkgen_freq))
        self.scope.glitch.repeat = length // (int(1e9) // int(self.scope.clock.clkgen_freq))
        self.scope.arm()

    def capture(self):
        self.scope.capture()

    def block(self, timeout=1):
        # TODO: set the timeout of scope.capture
        # blocks until scope triggered (or times out),
        # then disarms scope and copies data back.
        if self.scope.capture():
            raise Exception("Function execution timed out!")

    def power_cycle_target(self, power_cycle_time=0.2):
        if self.power_supply is not None:
            self.power_supply.power_cycle_target(power_cycle_time)
        else:
            self.scope.io.target_pwr = False
            time.sleep(power_cycle_time)
            self.scope.io.target_pwr = True

    def reset(self, reset_time=0.2):
        self.scope.io.nrst = 'low'
        time.sleep(reset_time)
        self.scope.io.nrst = 'high_z'

    def power_cycle_reset(self, power_cycle_time=0.2):
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

    def reset_and_eat_it_all(self, target, target_timeout=0.3):
        self.scope.io.nrst = 'low'
        target.ser.timeout = target_timeout
        target.read(4096)
        target.ser.timeout = target.timeout
        self.scope.io.nrst = 'high_z'

    def reset_wait(self, target, token, reset_time=0.2, debug=False):
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

    def set_lpglitch(self):
        self.scope.io.glitch_hp = False
        self.scope.io.glitch_lp = True

    def set_hpglitch(self):
        self.scope.io.glitch_hp = True
        self.scope.io.glitch_lp = False

    def rising_edge_trigger(self, dead_time, pin):
        # Note: dead_time and pin have no functions here (see PicoGlitcher.rising_edge_trigger)
        self.scope.io.tio4 = 'high_z'
        self.scope.trigger.triggers = 'tio4'

    def uart_trigger(self, pattern):
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
        self.scope.trigger.triggers = 'tio1'
        self.scope.trigger.module = 'DECODEIO'
        self.scope.decode_IO.rx_baud = 115200
        self.scope.decode_IO.decode_type = 'USART'
        self.scope.decode_IO.trigger_pattern = [pattern]
        #self.scope.io.hs2 = "clkgen"

    def disconnect(self):
        if self.scope is not None:
            print("[+] Disconnecting ChipWhisperer Pro")
            #self.scope.io.glitch_hp = False
            #self.scope.io.glitch_lp = False
            self.scope.dis()

    def reconnect(self, disconnect_wait=0.5):
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()

    def reconnect_with_uart(self, pattern, disconnect_wait=0.5):
        self.disconnect()
        time.sleep(disconnect_wait)
        self.init()
        self.uart_trigger(pattern)

    def __del__(self):
        self.disconnect()

class Helper():
    def timestamp():
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")