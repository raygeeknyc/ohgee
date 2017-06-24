import logging
_DEBUG = logging.INFO

import multiprocessing
from multiprocessingloghandler import ParentMultiProcessingLogHandler
import Queue
from array import array
import threading
import time
import io
import sys
import speechrecognizer
import speechanalyzer
import os, signal

global STOP
STOP = False

def signal_handler(sig, frame):
    global STOP
    logging.debug("INT signal trapped")
    if STOP:
        logging.debug("second INT signal trapped, killing")
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    STOP = True
signal.signal(signal.SIGINT, signal_handler)
 
def receiveSpeech(transcript):
    logging.info("listening")
    _, transcript = transcript
    try:
        while True:
            utterance = transcript.recv()
            print("Utterance: {}".format(utterance))
    except EOFError:
        logging.debug("done listening")

if __name__ == '__main__':
    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_DEBUG)
    transcript = multiprocessing.Pipe()

    recognition_worker = speechrecognizer.SpeechRecognizer(transcript, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.info("Starting speech recognition")
    recognition_worker.start()

    analysis_worker = speechanalyzer.SpeechAnalyzer(transcript, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.info("Starting speech analysis")
    analysis_worker.start()
    logging.info("analyzing speech")
    try:
        #listener = threading.Thread(target = receiveSpeech, args=(transcript,))
        #listener.start()
        logging.info("waiting")
        while not STOP:
            time.sleep(0.1)
        logging.info("stopping")
        i, _ = transcript
        i.close()
    except Exception, e:
        logging.error("Error in main: {}".format(e))
    finally:
        logging.info("ending main")
        recognition_worker.stop()
        analysis_worker.stop()
        logging.info("waiting for background processes to exit")
        recognition_worker.join()
        analysis_worker.join()
        logging.info("done")
    sys.exit()
