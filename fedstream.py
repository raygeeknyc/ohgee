#!/usr/bin/python3

from multiprocessingloghandler import ChildMultiProcessingLogHandler
import logging
import queue
import os

class FedStream(object):
    def __init__(self, source, log_queue, log_level):
        # Create a thread-safe buffer of audio data
        self._buff = source
        self.closed = False
        self._log_queue = log_queue
        self._log_level = log_level
        self._initLogging()

    def _initLogging(self):
        handler = ChildMultiProcessingLogHandler(self._log_queue)
        logging.getLogger(str(os.getpid())).addHandler(handler)
        logging.getLogger(str(os.getpid())).setLevel(self._log_level)

    def open(self):
        logging.debug("fedstream open()")
        self.closed = False

    def close(self):
        logging.debug("fedstream close()")
        self.closed = True

    # This is not the number of bytes and should only be used as an empty/non-empty indicator
    def available(self):
        return self._buff.qsize()

    def read(self, chunk_size):
        data = None
        while not data and not self.closed:
            try:
                data = [self._buff.get(timeout=0.1)]
            except queue.Empty:
                pass
        if not data:
            logging.debug("fedstream read() no data, closed")
            return

        # Now consume whatever other data's still buffered.
        while True:
            try:
                data.append(self._buff.get(block=False))
            except queue.Empty:
                break
        return b''.join(data)
