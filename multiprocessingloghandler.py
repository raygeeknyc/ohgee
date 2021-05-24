#!/usr/bin/python3

import multiprocessing, logging, sys, os, threading, time, Queue

class MultiProcessingLogHandler(logging.Handler):
    def __init__(self, queue):
        logging.Handler.__init__(self)
        self.queue = queue

    def _format_record(self, record):
        ei = record.exc_info
        if ei:
            dummy = self.format(record) # just to get traceback text into record.exc_text
            record.exc_info = None  # to avoid Unpickleable error
        return record

    def __del__(self):
        self.close()

class ParentMultiProcessingLogHandler(MultiProcessingLogHandler):
    def __init__(self, handler, queue):
        MultiProcessingLogHandler.__init__(self, queue)
        self._handler = handler
        formatter = logging.Formatter('%(asctime)s - %(module)s %(process)d %(thread)d - %(levelname)s - %(message)s')
        self._handler.setFormatter(formatter)
        self._shutdown = False
        self.polltime = 1
        self._receiver = threading.Thread(target=self.receive)
        self._receiver.daemon = True
        self._receiver.start()
    
    def receive(self):
        while (self._shutdown == False) or (self.queue.empty() == False):
            try:
                record = self.queue.get(True, self.polltime)
                self._handler.emit(record)
            except Queue.Empty, e:
                pass

    def close(self):
        time.sleep(self.polltime+1) # give some time for messages to enter the queue.
        self._shutdown = True
        time.sleep(self.polltime+1) # give some time for the server to time out and see the shutdown

    def emit(self, record):
        try:
            s = self._format_record(record)
            self._handler.emit(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

class ChildMultiProcessingLogHandler(MultiProcessingLogHandler):
    def __init__(self, queue):
        MultiProcessingLogHandler.__init__(self, queue)

    def send(self, s):
        self.queue.put(s)

    def emit(self, record):
        try:
            self.send(record)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

