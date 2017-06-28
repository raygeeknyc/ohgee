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

global STOP
STOP = False

def showGoodMood(score):
    print "Good mood {}".format(score)

def showBadMood(score):
    print "Bad mood {}".format(score)

def showMehMood():
    print "meh mood"

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
    except EOFError:
        logging.debug("done listening")

if __name__ == '__main__':
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
            time.sleep(0.1)
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
    sys.exit()
