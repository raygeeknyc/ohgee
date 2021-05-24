#!/usr/bin/python3

import logging
_DEBUG = logging.DEBUG

import threading
import time
import io
import sys
import os, signal

global waving
waving = False

def produceWork():
    global waving
    while True:
        while not waving:
            time.sleep(0.1)
        print("waving")
        time.sleep(2)
        print("done waving")
        waving = False

producer = threading.Thread(target=produceWork)
producer.start()
logging.debug("creating waver")
for i in range(10):
    print("main {}, waiting".format(i))
    time.sleep(2)
    if not waving:
        print("go")
        waving = True
print("final wait")
producer.join()
print "done"
