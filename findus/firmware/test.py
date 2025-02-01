title= "inlineG.py" # http://docs.micropython.org/en/v1.9.3/pyboard/pyboard/tutorial/assembler.html
# by CWE
from rp2 import *
from machine import *
from time import *
import uarray

@micropython.asm_thumb
def regPeek(r0): # Address
    mov(r1,r0)
    ldr(r0,[r1,0])

@micropython.asm_thumb
def regPoke(r0, r1): # Address, Data
    str(r1,[r0,0])
    mov(r0,r1)
    
def regSet(adress, mask):
    regPoke(adress, regPeek(adress) | mask)

@micropython.asm_thumb
def adcGet(r0, r1): # BufferAddress, Ctrl-Array

    b(Entry)
    #b(StartSample)
    
    label(GetAdc) # get one sample out of the fifo
    ldr(r2,[r1,0])
    ldrh(r2,[r2,10]) # read upper Half of FCS - something in the fifo?
    cmp(r2,0)
    bls(GetAdc)
    ldr(r2,[r1,0])
    ldr(r2,[r2,12]) # read FIFO
    bx(lr)
    
    label(Entry)
    mov(r4,r0) # BufferAdress
    ldr(r3,[r1,16]) # Trigger Level
    mov(r0,r3)

    #cpsid(1)
    bl(GetAdc) # empty fifo
    bl(GetAdc)
    bl(GetAdc)
    bl(GetAdc)
    bl(GetAdc)
    bl(GetAdc)
    
    label(WaitLow)
    bl(GetAdc)
    cmp(r2,r3)
    bgt(WaitLow)

    ldr(r3,[r1,20]) # Upper Trigger Level
    label(WaitHigh)
    bl(GetAdc)
    cmp(r3,r2)
    bgt(WaitHigh)
    
    label(StartSample)
    ldr(r3,[r1,8]) # Buffer Length
    label(GetNext)
    bl(GetAdc)
    strh(r2,[r4,0])
    add(r4,r4,2) # next address
    sub(r3,r3,1)
    cmp(r3,0)
    bhi(GetNext)
    
    #cpsie(1)
    label(End)

print("start")
led= Pin(25,Pin.OUT)

adc0=ADC(Pin(26))

ledData = uarray.array('i',[
                0xd0000000 + 0x010, # 0 SIO OUT
                0xd0000000 + 0x018, # 4 SIO OUT_CLR
                0xd0000000 + 0x014, # 8 SIO OUT_SET
                1<<25 # 12 LED MASK
                ])

rGPIO26= 0x4001c000+0x6c # S. 312
regPoke( rGPIO26, 1<<7 ) # switch off ADC0 input and output

adcBuf = uarray.array('h',range(0,20)) # 320 signed short

adcCtrl = uarray.array('i',[
    0x4004c000, # BASE 0 CS, 4 Result, 8 FCS, 12 FIFO, 16 DIV S. 570
    1, # 4 Status: 0 done, 1 start
    len(adcBuf), # 8
    1, # 12 trig sign 1= positive
    2048 - 100, # 16 trigLevel
    2048 + 100 # 20 trigger level
    ])

print(title)

adc0.read_u16() # set up the channel
print("channel initialized.")
maxSample= 48e6 # Hz
fSample= 250_000 # This is the sampling frequency!
div= int(maxSample/fSample)
print("Div:", div)
regPoke(0x4004c000 + 0x10, div<<8) # set DIV register
#print("Div:", "{0:b}".format(regPeek(0x4004c000 + 0x10)))

regSet(0x4004c000 + 0x08, 1) # set fifo enable
#print("CS:", "{0:b}".format(regPeek(0x4004c000 + 0x00)))

regSet(0x4004c000, 1<<3) # set startmany
#print("CS:", "{0:b}".format(regPeek(0x4004c000 + 0x00)))

#while True:
#print(adcGet(adcBuf, adcCtrl))
led(1)
adcGet(adcBuf, adcCtrl)
led(0)
for i in range(0,len(adcBuf)):
    print(adcBuf[i])