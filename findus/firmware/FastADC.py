import uarray
from machine import ADC

@micropython.asm_thumb
def read_memory(r0): # Address
    # r0 = *(uint32_t *)r1;
    mov(r1,r0)
    ldr(r0,[r1,0])

@micropython.asm_thumb
def write_memory(r0, r1): # Address, Data
    # *(uint32_t *)r0 = r1
    str(r1,[r0,0])
    mov(r0,r1)
    
def set_memory(adress, mask):
    write_memory(adress, read_memory(adress) | mask)

@micropython.asm_thumb
def adc_get(r0, r1): # BufferAddress, Ctrl-Array
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
    #cpsid(1)
    bl(GetAdc) # empty fifo
    bl(GetAdc)
    bl(GetAdc)
    bl(GetAdc)
    bl(GetAdc)
    bl(GetAdc)
    
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

class FastADC():
    def __init__(self):
        self.configure_adc()

    def configure_adc(self, number_of_samples:int = 1024, sampling_freq:int = 500_000):
        self.number_of_samples = number_of_samples
        rGPIO26 = 0x4001c000 + 0x6c # S. 312
        write_memory(rGPIO26, 1<<7) # switch off ADC0 input and output
        self.adc_buffer = uarray.array('h', range(0, number_of_samples))
        self.adc_control = uarray.array('i',[
            0x4004c000, # BASE 0 CS, 4 Result, 8 FCS, 12 FIFO, 16 DIV S. 570
            1, # 4 Status: 0 done, 1 start
            number_of_samples # 8
            ])
        _ = ADC(0)
        #adcx.read_u16() # set up the channel; disabled line since this leads to locks
        max_sample = 48e6 # Hz, TODO: this depends on the CPU frequency!
        div = int(max_sample / sampling_freq)
        write_memory(0x4004c000 + 0x10, div<<8) # set DIV register
        set_memory(0x4004c000 + 0x08, 1) # set fifo enable
        set_memory(0x4004c000, 1<<3) # set startmany

    def init_array(self):
        return self.adc_buffer

    def get_number_of_samples(self):
        return self.number_of_samples

    def read(self):
        adc_get(self.adc_buffer, self.adc_control)
        return self.adc_buffer