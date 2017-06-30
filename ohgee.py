import logging

# reorder as appropriate
_DEBUG = logging.DEBUG
_DEBUG = logging.INFO

import multiprocessing
from multiprocessingloghandler import ParentMultiProcessingLogHandler
import threading
import time
import io
import sys
import speechrecognizer
import speechanalyzer
import os, signal
import rgbled

global STOP
STOP = False

global mood_set_until
mood_set_until = 0
MOOD_SET_DURATION_SECS = 4
POLL_DELAY_SECS = 0.2

servoPin = 18
ARM_RELAXED_POSITION = 50
ARM_UP_POSITION = 160
ARM_DOWN_POSITION = 10
ARM_WAVE_DOWN_SECS = 0.5
ARM_WAVE_UP_SECS = 2

GREETINGS = [["hello"],["hi"],["good", "morning"], ["hey", "there"]]
FAREWELLS = [["goodbye"], ["farewell"], ["good", "night"], ["see","you"]]
def phraseMatch(tokens, phrases):
    return []

def greeted(tokens):
    return phraseMatch(tokens, GREETINGS)

def departed(tokens):
    return phraseMatch(tokens, FAREWELLS)

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

def showMehMood():
    print "meh mood"
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
                showMehMood()
            if  greeted(tokens):
                waveArm()
    except EOFError:
        logging.debug("done listening")

def lowerArm():
    arm.start(ARM_DOWN_POSITION)

def raiseArm():
    arm.start(ARM_UP_POSITION)

def relaxArm():
    arm.start(ARM_RELAXED_POSITION)

def waveArm():
    lowerArm()
    time.sleep(ARM_WAVE_DOWN_SECS)
    raiseArm()
    time.sleep(ARM_WAVE_UP_SECS)
    relaxArm()
    
if __name__ == '__main__':
    led = rgbled.RgbLed(rgbled.redPin, rgbled.greenPin, rgbled.bluePin)
    led.setColor(rgbled.OFF)

    GPIO.setup(servoPin, GPIO.OUT)
    arm = GPIO.PWM(servoPin, 50)

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
