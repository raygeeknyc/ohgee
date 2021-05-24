#!/usr/bin/python3

import logging
_DEBUG = logging.DEBUG

import multiprocessingloghandler
import StringIO
import multiprocessing
import threading
from collections import deque
import time
import io
import sys
import os, signal

global STOP
STOP = False

def signal_handler(sig, frame):
    global STOP
    if STOP:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    logging.debug("SIGINT")
    STOP = True
signal.signal(signal.SIGINT, signal_handler)

class Background(multiprocessing.Process):
    def __init__(self, transcript, log_queue, log_level):
        super(Background,self).__init__()
        i, o = transcript
        self._exit = multiprocessing.Event()
        logging.debug("Event initially {}".format(self._exit.is_set()))
        self._log_queue = log_queue
        self._log_level = log_level
        self._transcript = i
        self._stop_producing = False
        self._stop_processing = False
        self._work_queue = deque()

    def _initLogging(self):
        handler = multiprocessingloghandler.ChildMultiProcessingLogHandler(self._log_queue)
        logging.getLogger(str(os.getpid())).addHandler(handler)
        logging.getLogger(str(os.getpid())).setLevel(self._log_level)

    def stop(self):
        logging.debug("***background received shutdown")
        self._exit.set()

    def run(self):
        try:
            logging.debug("***background active")
            logging.debug("process %s (%d)" % (self.name, os.getpid()))
            logging.debug("creating producer")
            self._producer = threading.Thread(target=self.produceWork)
            logging.debug("creating processor")
            self._processor = threading.Thread(target=self.performWork)
            self._initLogging()
            logging.debug("starting processor")
            self._processor.start()
            logging.debug("starting producer")
            self._producer.start()
            logging.debug("waiting for exit event")
            self._exit.wait()
            logging.debug("exit event received")
 
        except Exception as e:
            logging.error("***background exception: {}".format(e))
        logging.debug("***background terminating")
        self._stopProducing()
        self._stopProcessing()
        self._producer.join()
        self._processor.join()

    def _stopProducing(self):
        self._stop_producing = True
    
    def _stopProcessing(self):
        self._stop_processing = True

    def produceWork(self):
        logging.debug("producing")
        i = 0
        while not self._stop_producing:
            self._work_queue.append(i)
            time.sleep(1)
            i+=1
        logging.debug("stopped producing")

    def performWork(self):
        logging.debug("performing")
        while not self._stop_processing:
            try:
                message = self._work_queue.pop() 
                self._transcript.send("i={}".format(message))
            except IndexError:
                pass
        logging.debug("stopped performing")

if __name__ == '__main__':
    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = multiprocessingloghandler.ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_DEBUG)

    logging.debug("starting main")
    transcript = multiprocessing.Pipe()
    background_process = Background(transcript, log_queue, logging.getLogger('').getEffectiveLevel())
    try:
        i, o = transcript
        background_process.start()
        logging.debug("waiting for messages")
        c = 0
        while not STOP:
            message = o.recv()
            logging.info("main received message: {}".format(message))
            c += 1
            if c > 5:
                break;
            time.sleep(2)
    except Exception as e:
        logging.error("Error in main: {}".format(e))
    logging.info("ending main")
    background_process.stop()
    logging.info("waiting for background process to exit")
    time.sleep(2)
    background_process.join()
    time.sleep(2)
    logging.info("logged: main done")
    logging.shutdown()
    logging.error("main post-logging")
    sys.exit() 
