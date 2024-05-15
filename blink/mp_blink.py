from machine import Pin, Timer

class MicroPythonScript():
    def __init__(self):
        self.timer = Timer()
        self.led = Pin("LED", Pin.OUT)

    def tick(self):
        self.led.toggle()

    def blink(self):
        self.timer.init(freq=2.5, mode=Timer.PERIODIC, callback=self.tick)