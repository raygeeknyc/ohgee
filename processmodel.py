import logging
_DEBUG = logging.DEBUG

import multiprocessing
import threading
import Queue
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
    STOP = True
signal.signal(signal.SIGINT, signal_handler)

class Background(multiprocessing.Process):
    def __init__(self, transcript):
        multiprocessing.Process.__init__(self)
        i, o = transcript
        self._exit = multiprocessing.Event()
        print("Event initially {}".format(self._exit.is_set()))
        self._transcript = i
        self._stop_producing = False
        self._stop_processing = False
        self._work_queue = Queue.Queue()
        self._ingester = threading.Thread(target=self.getWork)
        self._processor = threading.Thread(target=self.performWork)

    def stop(self):
        print("***background received shutdown")
        self._exit.set()

    def run(self):
        try:
            print("***background active")
            self._processor.start()
            self._ingester.start()
            self._exit.wait()
 
        except Exception, e:
            print("***background exception: {}".format(e))
        print("***background terminating")
        self.stop()
        self._stopProducing()
        self._stopProcessing()
        self._ingester.join()
        self._processor.join()

    def _stopProducing(self):
        self._stop_producing = True
    
    def _stopProcessing(self):
        self._stop_processing = True

    def getWork(self):
        print("producing")
        i = 0
        while not self._stop_producing:
            self._work_queue.put(i)
            time.sleep(1)
            i+=1
        print("stopped producing")

    def performWork(self):
        print("performing")
        while not self._stop_processing:
            try:
                message = self._work_queue.get(False) 
                self._transcript.send("i={}".format(message))
            except Queue.Empty:
                time.sleep(0.1)
        print("stopped performing")

def runWorker(background):
    logging.debug("starting background process")
    background.run()

if __name__=='__main__':
    logging.getLogger().setLevel(_DEBUG)

    logging.debug("starting main")
    transcript = multiprocessing.Pipe()
    
    worker = Background(transcript)
    try:
        i, o = transcript
        worker.start()
        logging.debug("waiting for messages")
        c = 0
        while not STOP:
            message = o.recv()
            logging.info("main received message: {}".format(message))
            c += 1
            if c > 5:
                break;
    except Exception, e:
        logging.error("Error in main: {}".format(e))
    logging.info("ending main")
    worker.stop()
    logging.info("waiting for background process to exit")
    worker.join()
    logging.info("done")
    sys.exit() 
