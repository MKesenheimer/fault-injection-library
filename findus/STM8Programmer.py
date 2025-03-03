import serial
import os
import math
import argparse
from time import sleep
import struct
import sys

def hex_int(value:str):
    return int(value, 16)

class STM8Programmer():
    BLOCK_SIZE = 64 # 128 for parts with >8k flash

    REQ_ENTER = (0xde, 0xad, 0xbe, 0xef, )
    BOOTLOADER_INIT = (0x7f, )
    WRITE_MEMORY = (0x10, )
    READ_MEMORY = (0x11, )
    OPTION_WRITE = (0x12, )
    OPTION_READ = (0x13, )

    ACK  = (0x79, )
    NACK = (0x1f, )

    def __init__(self, port, baud):
        try:
            self.ser = serial.Serial(port, baud, timeout=0.05)
        except:
            print(f"[+] Seriell port {port} not found. Exiting.")
            sys.exit(1)

    def __del__(self):
        try:
            self.ser.setRTS(0)
            self.ser.close()
        except:
            pass

    def crc8_update(self, data, crc):
        crc ^= data
        for _ in range(0, 8):
            if crc & 0x80 != 0:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
        return crc & 0xFF

    def calculate_crc(self, bts):
        crc = 0xff
        for b in bts:
            crc = self.crc8_update(b, crc)
        return crc

    def send_and_check(self, bts):
        crc = self.calculate_crc(bts)
        bts.extend([crc])
        #print(f"Sending {bts}")
        #print(f"crc = {hex(crc)}")
        self.ser.write(bts)
        #ser.flushOutput()
        ack = self.ser.read(1)
        if ack == bytearray(STM8Programmer.ACK):
            return b'ACK'
        elif ack == bytearray(STM8Programmer.NACK):
            return b'NACK'
        return b'warning: no response'

    def bootloader_enter(self):
        # toggle reset via DTR
        self.ser.setDTR(1)
        self.ser.setRTS(1)
        sleep(0.1)
        self.ser.setDTR(0)
        sleep(0.1)
        # send payload
        req = bytearray(STM8Programmer.BOOTLOADER_INIT)
        if self.send_and_check(req) != b'ACK':
            return b'error: bootloader enter failed'
        return b'success: bootloader enter succeeded'

    def write_memory(self, file):
        # sending write memory command
        if self.send_and_check(bytearray(STM8Programmer.WRITE_MEMORY)) != b'ACK':
            return b'error: sending write memory command failed'

        # sending number of chunks
        chunks = os.path.getsize(file)
        chunks = int(math.ceil(float(chunks) / STM8Programmer.BLOCK_SIZE))
        if self.send_and_check(bytearray((chunks, ))) != b'ACK':
            return b'error: sending number of chunks failed'

        # sending chunks
        data = open(file, 'rb')
        total = 0
        with data as f:
            chunk = bytearray(f.read(STM8Programmer.BLOCK_SIZE))
            while chunk:
                total += len(chunk)
                print(total)
                # padding
                chunk.extend([0xFF] * (STM8Programmer.BLOCK_SIZE - len(chunk)))
                if self.send_and_check(chunk) != b'ACK':
                    return b'error: sending chunk failed'
                chunk = bytearray(f.read(STM8Programmer.BLOCK_SIZE))

    def read_memory(self, address = 0x8000, length = 0xff):
        # sending read memory command
        if self.send_and_check(bytearray(STM8Programmer.READ_MEMORY)) != b'ACK':
            return b'error: sending read memory command failed', b''
    
        # sending address to read from
        address = struct.pack('>H', address)
        #print(address)
        if self.send_and_check(bytearray(address)) != b'ACK':
            return b'error: sending address to read from failed', b''
    
        # sending length
        if self.send_and_check(bytearray((length, ))) != b'ACK':
            return b'error: sending number of bytes to read failed', b''
    
        # read memory
        memory = self.ser.read(length + 1)
        crc = self.ser.read(1)
        if crc != bytes([self.calculate_crc(memory)]):
            return b'warning: bytes received, checksum wrong', memory

        return b'success:', memory

    def write_option_bytes(self, opt = 0x00):
        # sending option bytes command
        if self.send_and_check(bytearray(STM8Programmer.OPTION_WRITE)) != b'ACK':
            return b'error: sending option bytes command failed'

        # sending option byte to program
        if self.send_and_check(bytearray((opt, ))) != b'ACK':
            return b'error: sending option byte failed'

        return b'success: writing option byte successful'

    def read_option_bytes(self, length = 0x00):
        # sending option bytes command
        if self.send_and_check(bytearray(STM8Programmer.OPTION_READ)) != b'ACK':
            return b'error: sending option bytes command failed', b''

        # sending number of bytes to read
        if self.send_and_check(bytearray((length, ))) != b'ACK':
            return b'error: sending number of bytes to read failed', b''

        # read memory
        memory = self.ser.read(length + 1)
        crc = self.ser.read(1)
        if crc != bytes([self.calculate_crc(memory)]):
            return b'warning: option bytes received, checksum wrong', memory

        return b'success:', memory

    def bootloader_exec(self, args):
        response = self.bootloader_enter()
        print(response)
        if b'success' not in response:
            return

        if args.write is not None:
            response = self.write_memory(args.write)
            print(response)
            return
        
        if args.read is not None:
            response, mem = self.read_memory(args.read, args.number_of_bytes)
            print(response)
            print(mem)
            return

        if args.write_option is not None:
            response = self.write_option_bytes(args.write_option)
            print(response)
            return
        
        if args.read_option is not None:
            response, opt = self.read_option_bytes(args.read_option)
            print(response)
            print(opt)
            return

def main():
    parser = argparse.ArgumentParser(description='stm8-bootloader programmer')
    parser.add_argument('--port', '-p', required=True)
    parser.add_argument('--baud', '-b', default=115200)
    parser.add_argument('--write', '-w', required=False, help='firmware in binary format to flash to the microcontroller')
    parser.add_argument('--read', '-r', required=False, help='read bytes from address (as hex, e.g. 0x8000)', type=hex_int)
    parser.add_argument('--number-of-bytes', '-n', required=False, help='number of bytes to read', default=0xff, type=int)
    parser.add_argument('--write-option', '-wo', required=False, help='set the value of the rop option byte (as hex, e.g. 0x00)', type=hex_int)
    parser.add_argument('--read-option', '-ro', const='0x00', required=False, help='read the value of the rop option byte', type=hex_int, nargs='?')
    args = parser.parse_args()

    programmer = STM8Programmer(args.port, args.baud)
    programmer.bootloader_exec(args)

if __name__ == "__main__":
    main()
