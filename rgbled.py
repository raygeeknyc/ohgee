#!/usr/bin/python3

import time
import RPi.GPIO as GPIO
import threading
import sys

# Demo pin definitions:
redPin = 2
greenPin = 3
bluePin = 4
powerPin = 17

RED = (True, False, False)
GREEN = (False, True, False)
BLUE = (False, False, True)
WHITE = (True, True, True)
YELLOW = (True, True, False)
CYAN = (False, True, True)
MAGENTA = (True, False, True)
OFF = (False, False, False)

COLOR_CYCLE_SECS = 0.5

class RgbLed:
    GPIO.setmode(GPIO.BCM)

    def __init__(self, redPin, greenPin, bluePin, powerPin=None):

        self._redPin = redPin
        self._greenPin = greenPin
        self._bluePin = bluePin
        self._powerPin = powerPin

        GPIO.setup(self._redPin, GPIO.OUT)
        GPIO.setup(self._greenPin, GPIO.OUT)
        GPIO.setup(self._bluePin, GPIO.OUT)
        if powerPin is not None:
            GPIO.setup(self._powerPin, GPIO.OUT)
        
        self.setColor(OFF)

    def setColor(self, rgb):
        self._color = rgb
        if powerPin is not None:
            if rgb[0] or rgb[1] or rgb[2]:
                GPIO.output(self._powerPin, GPIO.HIGH)
            else:
                GPIO.output(self._powerPin, GPIO.LOW)
        GPIO.output(self._redPin, GPIO.LOW if rgb[0] else GPIO.HIGH)
        GPIO.output(self._greenPin, GPIO.LOW if rgb[1] else GPIO.HIGH)
        GPIO.output(self._bluePin, GPIO.LOW if rgb[2] else GPIO.HIGH)

    def stop(self):
        self._stop = True

    def cycle(self, interval_secs):
        self._interval_secs = interval_secs
        self.setColor(RED)
        self._stop = False
        while not self._stop:
            time.sleep(self._interval_secs)
            self._cycleColor()

    def _cycleColor(self):
        if self._color is RED:
            self.setColor(GREEN)
        elif self._color is GREEN:
            self.setColor(BLUE)
        elif self._color is BLUE:
            self.setColor(CYAN)
        elif self._color is CYAN:
            self.setColor(YELLOW)
        elif self._color is YELLOW:
            self.setColor(WHITE)
        elif self._color is WHITE:
            self.setColor(OFF)
        elif self._color is OFF:
            self.setColor(RED)

if __name__ == "__main__":
    demo = RgbLed(redPin, greenPin, bluePin, powerPin)
    demo.setColor(RED)
    time.sleep((COLOR_CYCLE_SECS))
    demo.setColor(GREEN)
    time.sleep((COLOR_CYCLE_SECS))
    demo.setColor(BLUE)
    time.sleep((COLOR_CYCLE_SECS))
    demo.setColor(OFF)
    time.sleep(2)
    demo.setColor(CYAN)
    time.sleep((COLOR_CYCLE_SECS))
    demo.setColor(YELLOW)
    time.sleep((COLOR_CYCLE_SECS))
    demo.setColor(MAGENTA)
    time.sleep((COLOR_CYCLE_SECS))
    demo.setColor(WHITE)
    time.sleep((COLOR_CYCLE_SECS))
    demo.setColor(OFF)

    sleepLed = threading.Thread(target = demo.cycle, args=(2,))
    sleepLed.start()
    response = input("waiting for you before stopping... ")
    demo.stop()
    print("waiting for LED to stop cycling")
    sleepLed.join()
    GPIO.cleanup()
    sys.exit()
