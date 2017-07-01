import logging

# reorder as appropriate
_DEBUG = logging.DEBUG
_DEBUG = logging.INFO

import multiprocessing
from multiprocessingloghandler import ParentMultiProcessingLogHandler
import threading
import RPi.GPIO as GPIO
import time
import io
import sys
import os, signal

import rgbled
import speechrecognizer
import speechanalyzer

global STOP
STOP = False
global waving
waving = False

global mood_set_until
mood_set_until = 0
MOOD_SET_DURATION_SECS = 4
POLL_DELAY_SECS = 0.2

servoPin = 18
ARM_RELAXED_POSITION = 7.5
ARM_UP_POSITION = 12.5
ARM_DOWN_POSITION = 2.5
ARM_WAVE_LOWER_SECS = 0.5
ARM_WAVE_RAISE_SECS = 2
ARM_WAVE_DELAY_SECS = 5

def expireMood():
    global mood_set_until
    if mood_set_until and mood_set_until < time.time():
        mood_set_until = 0
        led.setColor(rgbled.OFF)

def setMoodTime():
    global mood_set_until
    global MOOD_SET_DURATION_SECS
    mood_set_until = time.time() + MOOD_SET_DURATION_SECS

def showGoodMood(score):
    print "Good mood {}".format(score)
    led.setColor(rgbled.GREEN)
    setMoodTime()

def showBadMood(score):
    print "Bad mood {}".format(score)
    led.setColor(rgbled.RED)
    setMoodTime()

def showMehMood(score):
    print "Meh mood {}".format(score)
    led.setColor(rgbled.CYAN)
    setMoodTime()

def signal_handler(sig, frame):
    global STOP
    logging.debug("INT signal trapped")
    if STOP:
        logging.debug("second INT signal trapped, killing")
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    STOP = True
signal.signal(signal.SIGINT, signal_handler)
 
def wave():
    global waving
    while True:
        while not waving:
            time.sleep(ARM_WAVE_DELAY_SECS)
        logging.debug("wave")
        raiseArm()
        time.sleep(ARM_WAVE_RAISE_SECS)
        lowerArm()
        time.sleep(ARM_WAVE_LOWER_SECS)
        relaxArm()
        waving = False

def receiveLanguageResults(nl_results):
    logging.debug("listening")
    _, nl_results = nl_results
    try:
        while True:
            phrase = nl_results.recv()
            tokens, entities, sentiment = phrase
            if speechanalyzer.isGood(sentiment):
                showGoodMood(sentiment.score)
            elif speechanalyzer.isBad(sentiment):
                showBadMood(sentiment.score)
            else:
                showMehMood(sentiment.score)
            greeting = speechanalyzer.phraseMatch(tokens, speechanalyzer.GREETINGS)
            farewells = speechanalyzer.phraseMatch(tokens, speechanalyzer.FAREWELLS)
            if greeting:
                startWaving()
            if farewells:
                startWaving()
    except EOFError:
        logging.debug("done listening")

def lowerArm():
    arm.ChangeDutyCycle(ARM_DOWN_POSITION)

def raiseArm():
    arm.ChangeDutyCycle(ARM_UP_POSITION)

def relaxArm():
    arm.ChangeDutyCycle(ARM_RELAXED_POSITION)

def startWaving():
    global waving
    if not waving:
        waving = True
    
if __name__ == '__main__':
    led = rgbled.RgbLed(rgbled.redPin, rgbled.greenPin, rgbled.bluePin)
    led.setColor(rgbled.OFF)

    GPIO.setup(servoPin, GPIO.OUT)
    arm = GPIO.PWM(servoPin, 50)
    arm.start(ARM_RELAXED_POSITION)

    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_DEBUG)
    transcript = multiprocessing.Pipe()
    nl_results = multiprocessing.Pipe()

    recognition_worker = speechrecognizer.SpeechRecognizer(transcript, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting speech recognition")
    recognition_worker.start()

    analysis_worker = speechanalyzer.SpeechAnalyzer(transcript, nl_results, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting speech analysis")
    analysis_worker.start()
    try:
        waver = threading.Thread(target = wave, args=())
        waver.start()
        listener = threading.Thread(target = receiveLanguageResults, args=(nl_results,))
        listener.start()
        logging.debug("waiting")
        while not STOP:
            time.sleep(POLL_DELAY_SECS)
            expireMood()
        logging.debug("stopping")
        _, i = nl_results
        i.close()
    except Exception, e:
        logging.error("Error in main: {}".format(e))
    finally:
        logging.debug("ending main")
        recognition_worker.stop()
        analysis_worker.stop()
        logging.debug("waiting for background processes to exit")
        recognition_worker.join()
        analysis_worker.join()
        logging.debug("done")
        led.setColor(rgbled.OFF)
    GPIO.cleanup()
    sys.exit()
