import sqlite3
import time
import serial
import sys
#import chipwhisperer as cw
import datetime
from termcolor import colored
import os
import glob

import pyboard

class Database():
    def __init__(self, argv, dbname=None, resume=False):
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

        self.base_row_count = self.get_number_of_experiments()
        if resume or dbname is not None:
            print(f"[+] Number of experiments in previous database: {self.base_row_count}")

    def insert(self, experiment_id, delay, length, color, response):
        if (experiment_id + self.base_row_count) == 0:
            s_argv = ' '.join(self.argv[1:])
            self.cur.execute("INSERT INTO metadata (stime_seconds,argv) VALUES (?,?)", [int(time.time()), s_argv])
        self.cur.execute("INSERT INTO experiments (id,delay,length,color,response) VALUES (?,?,?,?,?)", [experiment_id + self.base_row_count, delay, length, color, response])
        self.con.commit()

    def remove(self, experiment_id):
        self.cur.execute("DELETE FROM experiments WHERE id = (?);", [experiment_id + self.base_row_count])
        self.con.commit()

    def get_number_of_experiments(self):
        self.cur.execute("SELECT count(id) FROM experiments")
        result = self.cur.fetchone()
        row_count = result[0]
        return row_count

    def get_base_experiments_count(self):
        return self.base_row_count

    def close(self):
        self.con.close()

class Database_New():
    def __init__(self, argv):
        self.argv = argv

        script_name = os.path.basename(self.argv[0])
        self.dbname = f"{script_name}_%s.sqlite" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not os.path.isdir('databases'):
            os.mkdir("databases")
        
        self.con = None
        self.cur = None
        self.init()

    def open(self):
        database_path = os.path.join('database/',self.dbname)
        self.con = sqlite3.connect(database_path, timeout=10)
        self.cur = self.con.cursor()

    def close(self):
        if self.cur is not None:
            self.cur.close()
        if self.con is not None:
            self.con.close()

    def init(self):
        self.open()
        self.cur.execute("CREATE TABLE experiments(id integer, delay integer, length integer, color text, response blob)")
        self.cur.execute("CREATE TABLE metadata (stime_seconds integer, argv blob)")        
        self.close()

    def insert(self,experiment_id, delay, length, color, response):
        self.open()
        if experiment_id == 0:
            s_argv = ' '.join(self.argv[1:])
            self.cur.execute("INSERT INTO metadata (stime_seconds,argv) VALUES (?,?)", [int(time.time()), s_argv])
        self.cur.execute("INSERT INTO experiments (id,delay,length,color,response) VALUES (?,?,?,?,?)", [experiment_id, delay, length, color, response])
        self.con.commit()
        self.close()


class DatabaseRCG():
    def __init__(self, argv):
        script_name = os.path.basename(sys.argv[0])
        self.dbname = f"{script_name}_%s.sqlite" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if not os.path.isdir('databases'):
            os.mkdir("databases")
        self.con = sqlite3.connect("databases/" + self.dbname)
        self.cur = self.con.cursor()
        self.argv = argv
        self.cur.execute("CREATE TABLE experiments(id integer, clock integer, delay integer, length integer, color text, response blob)")
        self.cur.execute("CREATE TABLE metadata (stime_seconds integer, argv blob)")

    def insert(self,experiment_id, clock, delay, length, color, response):
        if experiment_id == 0:
            s_argv = ' '.join(self.argv[1:])
            self.cur.execute("INSERT INTO metadata (stime_seconds,argv) VALUES (?,?)", [int(time.time()), s_argv])
        self.cur.execute("INSERT INTO experiments (id,clock,delay,length,color,response) VALUES (?,?,?,?,?,?)", [experiment_id, clock,delay, length, color, response])
        self.con.commit()

    def close(self):
        self.con.close()


class Serial():
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, timeout=0.1, bytesize=8, parity='E', stopbits=1):
        self.ser = None
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.init()

    def init(self):
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout, bytesize=self.bytesize, parity=self.parity, stopbits=self.stopbits)

    def write(self, message):
        self.ser.write(message)

    def read(self, length):
        response = self.ser.read(length)
        return response
    
    def reset(self, debug=False):
        print("[+] Resetting target...")
        self.ser.dtr = True
        time.sleep(0.1)
        self.ser.dtr = False
        response = self.ser.read(4096)
        if debug:
            for line in response.splitlines():
                print('\t', line.decode())
        return False

    def empty_read_buffer(self):
        self.ser.reset_input_buffer()

    def empty_read_buffer_v2(self, timeout=0.01):
        self.ser.timeout = timeout
        self.ser.read(8192)
        self.ser.timeout = self.timeout

    def close(self):
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

    def reset_low(self):
        self.pyb.exec('mp.reset_low()')

    def reset_high(self):
        self.pyb.exec('mp.reset_high()')

    def reset(self, reset_time):
        self.pyb.exec(f'mp.reset({reset_time})')

    def block(self):
        self.pyb.exec('mp.block()')

    def get_sm2_output(self):
        return self.pyb.exec('mp.get_sm2_output()')


class PicoGlitcher():
    def __init__(self):
        self.pico_glitcher = None

    def init(self, args):
        self.pico_glitcher = PicoGlitcherInterface()
        self.pico_glitcher.init(args.rpico, 'mp_glitcher')
        self.pico_glitcher.set_trigger("tio")
        self.pico_glitcher.set_frequency(200_000_000)
        
    def arm(self, delay, length):
        self.pico_glitcher.arm(delay, length)

    def block(self):
        self.pico_glitcher.block()

    def get_sm2_output(self):
        return self.pico_glitcher.get_sm2_output()

    def classify(self, expected, response):
        if response == expected:
            color = 'G'
        elif b'Falling' in response:
            color = 'R'
        elif b'Fatal exception' in response:
            color = 'M'
        else:
            color = 'Y'
        return color

    def reset(self, reset_time=0.2):
        self.pico_glitcher.reset_low()
        time.sleep(reset_time)
        self.pico_glitcher.reset_high()

    def power_cycle_target(self, power_cycle_time=0.2):
        self.pico_glitcher.power_cycle_target(power_cycle_time)

    def reset_and_eat_it_all(self, target, target_timeout=0.3):
        self.pico_glitcher.reset_low()
        target.ser.timeout = target_timeout
        target.read(4096)
        target.ser.timeout = target.timeout
        self.pico_glitcher.reset_high()

    def reset_wait(self, target, token, reset_time=0.2, debug=False):
        self.pico_glitcher.reset_low()
        time.sleep(reset_time)
        self.pico_glitcher.reset_high()

        response = target.read(4096)
        for _ in range(0, 5):
            if token in response:
                break
            response += target.read(4096)

        if debug:
            for line in response.splitlines():
                print('\t', line.decode())

    def colorize(self, s, color):
        colors = { 
            'G': 'green', 
            'Y': 'yellow', 
            'R': 'red', 
            'M': 'magenta',
        }
        return colored(s, colors[color])
    
    def get_speed(self, start_time, number_of_experiments):
        elapsed_time = int(time.time()) - start_time
        if elapsed_time == 0:
            return 'NA'
        else:
            return number_of_experiments // elapsed_time

    def uart_trigger(self, pattern):
        self.pico_glitcher.set_trigger("uart")
        self.pico_glitcher.set_baudrate(115200)
        self.pico_glitcher.set_pattern_match(pattern)