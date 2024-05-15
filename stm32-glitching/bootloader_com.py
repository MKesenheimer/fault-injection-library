import serial
import time
from functools import reduce

NACK = b'\x1f'
ACK  = b'\x79'

verbose = False

def check_ack(ser):
    s = ser.read(1)
    if s != ACK:
        #print(s)
        return 0
    return 1

def bootloader_setup_memread(ser):
    # init bootloader
    ser.write(b'\x7f')
    if check_ack(ser) == 0:
        return -1

    # read chip id if necessary
    if 0:
        # get chip id (x02: chip id, xfd: crc)
        ser.write(b'\x02\xfd')
        if check_ack(ser) == 0:
            return -2
        s = ser.read(3)
        id = s[1:3]
        print(f"Chip ID: {id}")
        if check_ack(ser) == 0:
            return -3

    # read memory (x11: read memory, xee: crc)
    ser.write(b'\x11\xee')
    # if rdp is activated, a nack is returned (x1f)
    if check_ack(ser) == 0:
        if verbose:
            print("RDP is active. Can not read memory.")
        return -4
    else:
        if verbose:
            print("RDP is not active. Memory read command available.")
    return 0

def bootloader_read_memory(ser, start, size):
    # write memory address
    startb = start.to_bytes(4, 'big')
    crc = reduce(lambda x, y: x ^ y, startb, 0).to_bytes(1, 'big')
    ser.write(startb)
    ser.write(crc)
    if check_ack(ser) == 0:
        return -5, b''

    # write bytes to read
    sizeb = size.to_bytes(1, 'big')
    crc = reduce(lambda x, y: x ^ y, sizeb, 0xff).to_bytes(1, 'big')
    # write number of bytes to read
    ser.write(sizeb)
    ser.write(crc)
    if check_ack(ser) == 0:
        return -6, b''

    time.sleep(0.1)

    # get memory
    mem = ser.read(size)
    return 0, mem


if __name__ == "__main__":
    ser = serial.Serial(port="/dev/tty.usbserial-21101", baudrate=115200, timeout=0.25, bytesize=8, parity='E', stopbits=1)

    start = 0x08000000
    size  = 0xff
    ret = bootloader_setup_memread(ser)
    if ret == 0:
        ret, mem = bootloader_read_memory(ser, start, size)
        if ret == 0:
            print(mem)
        else:
            print(ret)
    else:
        print(ret)
    ser.close()