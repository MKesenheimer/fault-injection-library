import rp2
from machine import Pin
import time

# === Program 1: Blink ===
@rp2.asm_pio(set_init=(rp2.PIO.OUT_LOW))
def blink_prog():
    wrap_target()
    set(pins, 1)
    set(pins, 0)
    nop()[31]
    nop()[31]
    wrap()

# === Program 2: Pulse ===
@rp2.asm_pio(set_init=(rp2.PIO.OUT_LOW))
def pulse_prog():
    wrap_target()
    set(pins, 1)
    nop()[31]
    set(pins, 0)
    nop()[31]
    wrap()

# Initialize a pin for output
pin = Pin("LED", Pin.OUT)
pin.low()

# Use State Machine 0
sm = rp2.StateMachine(0)

# Function to load and start a PIO program
def load_program(prog):
    sm.active(0)  # Stop state machine
    rp2.PIO(0).remove_program(prog)
    rp2.PIO(0).add_program(prog)
    sm.init(prog, freq=10000, set_base=pin)
    sm.active(1)

# Run Blink program
print("Running blink...")
load_program(blink_prog)
time.sleep(3)

# Switch to Pulse program
print("Switching to pulse...")
load_program(pulse_prog)
time.sleep(3)

# Stop the state machine
sm.active(0)
print("Done.")