# Copyright (C) 2024 Dr. Matthias Kesenheimer - All Rights Reserved.
# You may use, distribute and modify this code under the terms of the GPL3 license.
#
# You should have received a copy of the GPL3 license with this file.
# If not, please write to: info@faultyhardware.de.

from rp2 import asm_pio, PIO
import Globals

@asm_pio(set_init=(PIO.OUT_LOW), sideset_init=(PIO.OUT_LOW))
def glitch():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until length received
    pull(block)
    mov(y, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 1).side(0b1)
    # set irq0 which starts the adc callback (if enabled)
    irq(0)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # emit glitch at base pin
    set(pins, 0b1)
    label("length_loop")       
    jmp(y_dec, "length_loop")

    # stop glitch and disable pin_glitch_en
    set(pins, 0b0).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(set_init=(PIO.OUT_LOW), sideset_init=(PIO.OUT_LOW), out_shiftdir=PIO.SHIFT_RIGHT)
def glitch_burst():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until pulse config (length and delay between pulses) received, backup in isr
    pull(block)
    mov(isr, osr)
    # block until number of pulses received
    pull(block)
    mov(y, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 1).side(0b1)
    # set irq0 which starts the adc callback (if enabled)
    irq(0)

    # delay until first glitch
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # emit a certain number of glitches
    label("burst_loop")

    # copy config into osr
    mov(osr, isr)
    out(x, 16) # length = OSR >> 16

    # emit glitch
    set(pins, 0b1)
    label("length_loop")       
    jmp(x_dec, "length_loop")
    set(pins, 0b0)

    # wait until next glitch
    out(x, 16) # delay = OSR >> 16
    label("delay2_loop")       
    jmp(x_dec, "delay2_loop")

    jmp(y_dec, "burst_loop")

    # reset glitch_en
    set(pins, 0b0).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(set_init=(PIO.OUT_LOW), sideset_init=(PIO.OUT_LOW), out_shiftdir=PIO.SHIFT_RIGHT)
def glitch_multiple():
    # block until number of pulses received
    pull(block)
    mov(y, osr)
    
    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 1).side(0b1)
    # set irq0 which starts the adc callback (if enabled)
    irq(0)

    # emit multiple glitches given by each config
    label("glitch_loop")

    # block until first config is received
    pull(block)
    out(x, 22) # delay = OSR >> 22

    # delay until first glitch
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # get the length
    out(x, 10) # length = OSR >> 10

    # emit glitch at base pin
    set(pins, 0b1)
    label("length_loop")       
    jmp(x_dec, "length_loop")
    set(pins, 0b0)

    jmp(y_dec, "glitch_loop")

    # stop glitch and disable pin_glitch_en
    set(pins, 0b0).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(set_init=(PIO.OUT_HIGH), sideset_init=(PIO.OUT_LOW))
def pulse_shaping():
    # block until delay received
    pull(block)
    mov(x, osr)
    # block until total length of pulse received
    pull(block)
    mov(y, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 1).side(0b1)
    # set irq0 which starts the adc callback (if enabled)
    irq(0)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # set trigger pin low (start pulse generator)
    set(pins, 0b0)
    label("length_loop")
    jmp(y_dec, "length_loop")

    # stop pulse and disable pin_glitch_en
    set(pins, 0b1).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(set_init=(Globals.MUX1_PIO_INIT, Globals.MUX0_PIO_INIT), out_init=(Globals.MUX1_PIO_INIT, Globals.MUX0_PIO_INIT), sideset_init=(PIO.OUT_LOW), out_shiftdir=PIO.SHIFT_RIGHT)
def multiplex(MUX_PIO_INIT=Globals.MUX_PIO_INIT):
    # block until delay received
    pull(block)
    mov(x, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 1).side(0b1)
    # set irq0 which starts the adc callback (if enabled)
    irq(0)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # do the following two times
    set(x, 1)
    label("for_loop")

    # block until config received
    pull(block)
    out(pins, 2)
    out(y, 14) # t = OSR >> 14
    label("t1_loop")
    jmp(y_dec, "t1_loop")

    out(pins, 2)
    out(y, 14) # t = OSR >> 14
    label("t2_loop")
    jmp(y_dec, "t2_loop")

    # for loop
    jmp(x_dec, "for_loop")

    # reset and disable pin_glitch_en
    set(pins, MUX_PIO_INIT).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(set_init=(PIO.OUT_LOW, PIO.OUT_LOW), out_init=(PIO.OUT_LOW, PIO.OUT_LOW), sideset_init=(PIO.OUT_LOW), out_shiftdir=PIO.SHIFT_RIGHT)
def multiplex_vin1(MUX_PIO_INIT=0b00):
    # block until delay received
    pull(block)
    mov(x, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 1).side(0b1)
    # set irq0 which starts the adc callback (if enabled)
    irq(0)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # do the following two times
    set(x, 1)
    label("for_loop")

    # block until config received
    pull(block)
    out(pins, 2)
    out(y, 14) # t = OSR >> 14
    label("t1_loop")
    jmp(y_dec, "t1_loop")

    out(pins, 2)
    out(y, 14) # t = OSR >> 14
    label("t2_loop")
    jmp(y_dec, "t2_loop")

    # for loop
    jmp(x_dec, "for_loop")

    # reset and disable pin_glitch_en
    set(pins, MUX_PIO_INIT).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio(set_init=(PIO.OUT_LOW, PIO.OUT_HIGH), out_init=(PIO.OUT_LOW, PIO.OUT_HIGH), sideset_init=(PIO.OUT_LOW), out_shiftdir=PIO.SHIFT_RIGHT)
def multiplex_vin2(MUX_PIO_INIT=0b10):
    # block until delay received
    pull(block)
    mov(x, osr)

    # wait for trigger condition
    # enable pin_glitch_en
    wait(1, irq, 1).side(0b1)
    # set irq0 which starts the adc callback (if enabled)
    irq(0)

    # wait delay
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # do the following two times
    set(x, 1)
    label("for_loop")

    # block until config received
    pull(block)
    out(pins, 2)
    out(y, 14) # t = OSR >> 14
    label("t1_loop")
    jmp(y_dec, "t1_loop")

    out(pins, 2)
    out(y, 14) # t = OSR >> 14
    label("t2_loop")
    jmp(y_dec, "t2_loop")

    # for loop
    jmp(x_dec, "for_loop")

    # reset and disable pin_glitch_en
    set(pins, MUX_PIO_INIT).side(0b0)

    # tell execution finished (fills the sm's fifo buffer)
    push(block)

@asm_pio()
def tio_trigger_with_dead_time_rising_edge():
    # wait for irq in block_rising_condition or block_falling_condition state machine (dead time)
    wait(1, irq, 2)

    # wait for rising edge on trigger pin
    wait(0, pin, 0)
    wait(1, pin, 0)

    # tell observed trigger
    irq(block, 1)
    push(block)

@asm_pio()
def tio_trigger_with_dead_time_falling_edge():
    # wait for irq in block_rising_condition or block_falling_condition state machine (dead time)
    wait(1, irq, 2)

    # wait for falling edge on trigger pin
    wait(1, pin, 0)
    wait(0, pin, 0)

    # tell observed trigger
    irq(block, 1)
    push(block)

@asm_pio()
def edge_trigger_rising_edge():
    # block until number of edges received
    pull(block)
    mov(x, osr)

    # count the rising edges on trigger pin
    label("edge_count_loop")

    # wait for rising edge on trigger pin
    wait(0, pin, 0)
    wait(1, pin, 0)

    # decrease x and jump to the beginning of the loop
    jmp(x_dec, "edge_count_loop")

    # tell observed trigger
    irq(block, 1)
    push(block)

@asm_pio()
def edge_trigger_falling_edge():
    # block until number of edges received
    pull(block)
    mov(x, osr)

    # count the falling edges on trigger pin
    label("edge_count_loop")

    # wait for falling edge on trigger pin
    wait(1, pin, 0)
    wait(0, pin, 0)

    # decrease x and jump to the beginning of the loop
    jmp(x_dec, "edge_count_loop")

    # tell observed trigger
    irq(block, 1)
    push(block)

@asm_pio(in_shiftdir=PIO.SHIFT_RIGHT, out_shiftdir=PIO.SHIFT_LEFT)
def uart_trigger():
    # block until pattern received
    pull(block)
    mov(x, osr)
    # block until number of bits (self.number_of_bits - 1) received, store in osr
    pull(block)

    label("start")
    mov(isr, null)
    # Wait for start bit
    wait(0, pin, 0)
    # Preload bit counter, delay until eye of first data bit
    #set(y, BITS - 1) [10]
    mov(y, osr) [10]

    # Loop 9 times
    label("bitloop")
    # Sample data, shift sampled data into ISR
    in_(pins, 1)
    # Each iteration is 8 cycles
    jmp(y_dec, "bitloop") [6]

    # compare received data with supplied pattern
    mov(y, isr)
    jmp(x_not_y, "start")

    # if received data matches pattern, set the irq and activate the glitch
    irq(block, 1)
    push(block)

    # wrap around # TODO: ist hier ein wrap überhaupt notwendig?
    jmp("start")

@asm_pio()
def block_rising_condition():
    # block until dead time parameters received
    pull(block)
    mov(x, osr)

    # wait for rising edge condition
    wait(1, pin, 0)

    # wait dead time
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # tell execution finished
    irq(block, 2)
    push(block)

@asm_pio()
def block_falling_condition():
    # block until dead time parameters received
    pull(block)
    mov(x, osr)

    # wait for falling edge condition
    wait(0, pin, 0)

    # wait dead time
    label("delay_loop")
    jmp(x_dec, "delay_loop")

    # tell execution finished
    irq(block, 2)
    push(block)