import logging
_DEBUG = logging.DEBUG

import multiprocessing
import Queue
from array import array
import threading
import time
import io
import sys
import speechprocessor
import os, signal

global STOP
STOP = False

def signal_handler(sig, frame):
    global STOP
    print("signal trapped")
    if STOP:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    print("STOP")
    STOP = True
signal.signal(signal.SIGINT, signal_handler)
 
def receiveSpeech(transcript):
    logging.info("listening")
    i, o = transcript
    try:
        while True:
            utterance = o.recv()
            logging.info("Utterance: {}".format(utterance))
    except EOFError:
        logging.debug("done listening")

if __name__ == '__main__':
    logging.getLogger().setLevel(_DEBUG)
    transcript = multiprocessing.Pipe()
    speech_worker = speechprocessor.SpeechProcessor(transcript)
    logging.info("Starting speech analysis")
    speech_worker.start()
    logging.info("Receiving speech")
    try:
        listener = threading.Thread(target = receiveSpeech, args=(transcript,))
        listener.start()
        logging.info("polling")
        while not STOP:
            pass
        logging.info("stopping")
        o, i = transcript
        o.close()
        speech_worker.stop()
    except Exception, e:
        logging.error("Error in main: {}".format(e))
    logging.info("ending main")
    speech_worker.stop()
    logging.info("waiting for background process to exit")
    speech_worker.join()
    logging.info("done")
    sys.exit()
