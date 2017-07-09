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
import Queue

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
ARM_RELAXED_POSITION = 10.5
ARM_DOWN_POSITION = 12.5
ARM_UP_POSITION = 7.5
ARM_WAVE_LOWER_SECS = 0.5
ARM_WAVE_RAISE_SECS = 2
ARM_WAVE_DELAY_SECS = 1

SPEECH_TMP_FILE="/tmp/speech.wav"
PICO_CMD='pico2wave -l en-US --wave "%s" "%s";aplay "%s"'

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
    logging.info("Good mood {}".format(score))
    led.setColor(rgbled.GREEN)
    setMoodTime()

def showBadMood(score):
    logging.info("Bad mood {}".format(score))
    led.setColor(rgbled.RED)
    setMoodTime()

def showMehMood(score):
    logging.info("Meh mood {}".format(score))
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
 
def speak(speech_queue):
    global STOP
    logging.debug("speaker started")
    while not STOP:
        logging.debug("waiting to talk")
        utterance = " ".join(speech_queue.get())
        recognition_worker.suspendListening()
        logging.debug("saying {}".format(utterance))
        os.system(PICO_CMD % (SPEECH_TMP_FILE, utterance, SPEECH_TMP_FILE))
        recognition_worker.resumeListening()
    logging.debug("speaker stopping")

def wave():
    global waving
    global STOP
    while not STOP:
        while not waving:
            time.sleep(ARM_WAVE_DELAY_SECS)
        logging.debug("wave")
        raiseArm()
        time.sleep(ARM_WAVE_RAISE_SECS)
        lowerArm()
        time.sleep(ARM_WAVE_LOWER_SECS)
        relaxArm()
        time.sleep(0.5)
        arm.ChangeDutyCycle(0)
        waving = False

def receiveLanguageResults(nl_results):
    logging.debug("listening")
    _, nl_results = nl_results
    try:
        while True:
            phrase = nl_results.recv()
            text, tokens, entities, sentiment = phrase
            logging.debug("got spoken phrase {}".format(text))
            if speechanalyzer.isGood(sentiment):
                showGoodMood(sentiment.score)
            elif speechanalyzer.isBad(sentiment):
                showBadMood(sentiment.score)
            else:
                showMehMood(sentiment.score)
            response = speechanalyzer.getResponse(text)
            if response:
                logging.debug("phrase matched")
                comeback, wave_flag = response
                speech_queue.put(comeback)
                if wave_flag:
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
    unused, _ = nl_results
    unused.close()
    try:
        arm = GPIO.PWM(servoPin, 50)
        arm.start(0)
        waver = threading.Thread(target = wave, args=())
        waver.start()
        speech_queue = Queue.Queue()
        speaker = threading.Thread(target = speak, args=(speech_queue,))
        speaker.start()
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
        arm.stop()
    GPIO.cleanup()
    sys.exit()
