import logging
_DEBUG = logging.DEBUG

# Import the packages we need for drawing and displaying images
from PIL import Image

from picamera import PiCamera

# Imports the Google Cloud client packages we need
from google.cloud import vision
from google.cloud.vision.likelihood import Likelihood

import multiprocessing
from multiprocessingloghandler import ParentMultiProcessingLogHandler
from multiprocessingloghandler import ChildMultiProcessingLogHandler
import io
import sys
import os
import time
import signal
import Queue
import threading

# This is the desired resolution of the Pi camera
RESOLUTION = (320, 240)
CAPTURE_RATE_FPS = 2
# This is over an observed covered camera's noise
TRAINING_SAMPLES = 5
# This is how much the green channel has to change to consider a pixel changed
PIXEL_SHIFT_SENSITIVITY = 30

# This is how long to check for a shutdown
POLL_SECS = 0.5

def signal_handler(sig, frame):
    global STOP
    if STOP:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    logging.debug("SIGINT")
    STOP = True
signal.signal(signal.SIGINT, signal_handler)

class ImageAnalyzer(multiprocessing.Process):
    def __init__(self, vision_queue, log_queue, logging_level):
        multiprocessing.Process.__init__(self)
        self._log_queue = log_queue
        self._logging_level = logging_level
        self._exit = multiprocessing.Event()
        self._vision_queue, _ = vision_queue
        self._stop_capturing = False
        self._stop_analyzing = False
        self._last_frame_at = 0.0
        self._frame_delay_secs = 1.0/CAPTURE_RATE_FPS

    def stop(self):
        logging.debug("***analysis received shutdown")
        self._exit.set()

    def _initLogging(self):
        handler = ChildMultiProcessingLogHandler(self._log_queue)
        logging.getLogger(str(os.getpid())).addHandler(handler)
        logging.getLogger(str(os.getpid())).setLevel(self._logging_level)

    def capturePilFrame(self):
        self._image_buffer.seek(0)
        self._camera.capture(self._image_buffer, format="jpeg")
        self._image_buffer.seek(0)
        image = Image.open(self._image_buffer)
        image = image.load()
        self._last_frame_at = time.time()
        return image

    def getNextFrame(self):
        delay = (self._last_frame_at + self._frame_delay_secs) - time.time()
        if delay > 0:
            time.sleep(delay)
        self._current_frame = self.capturePilFrame()

    def calculateImageDifference(self):
        "Detect changes in the green channel."
        changed_pixels = 0
        for x in xrange(self._camera.resolution[0]):
            for y in xrange(self._camera.resolution[1]):
                if abs(self._current_frame[x,y][1] - self._prev_frame[x,y][1]) > PIXEL_SHIFT_SENSITIVITY:
                    changed_pixels += 1
        self._prev_frame = self._current_frame
        return changed_pixels

    def trainMotion(self):
        self._camera.start_preview(fullscreen=False, window=(100,100,self._camera.resolution[0], self._camera.resolution[1]))
        self._motion_threshold = 9999
        self.getNextFrame()
        self._prev_frame = self.capturePilFrame()
        for i in range(TRAINING_SAMPLES):
            self.getNextFrame()
            motion = self.calculateImageDifference()
            self._motion_threshold = min(motion, self._motion_threshold)
        self._camera.stop_preview()

    def run(self):
        self._initLogging()
        try:
            self._frames = Queue.Queue()
            self._stop_capturing = False
            self._stop_analyzing = False
            self._capturer = threading.Thread(target=self.captureFrames)
            self._capturer.start()
            self._analyzer = threading.Thread(target=self.analyzeVision)
            self._analyzer.start()
            while not self._exit.is_set():
                time.sleep(POLL_SECS)
            logging.debug("Shutting down threads")
            self._stop_capturing = True
            self._capturer.join()
            self._stop_analyzing = True
            self._analyzer.join()
        except Exception, e:
            logging.exception("Error in vision main thread {}".format(e))
        finally:
            logging.debug("Exiting vision")
            sys.exit(0)

    def analyzeVision(self):
        while not self._stop_analyzing:
            while True:
                frame = None
                try:
                    f = self._frames.get(block=False)
                    frame = f
                except Queue.Empty:
                    break
            if frame:
                logging.debug("Trailing frame read")
        logging.debug("Exiting vision analyze thread")

    def captureFrames(self):
        self._image_buffer = io.BytesIO()
        self._camera = PiCamera()
        self._camera.resolution = RESOLUTION
        prev_array = None
        logging.info("Training motion detection")
        self.trainMotion()
        logging.info("Trained motion detection {}".format(self._motion_threshold))
        while not self._stop_capturing:
            try:
                self.getNextFrame()
                motion = self.calculateImageDifference()
                if motion > self._motion_threshold:
                    logging.info("motion={}".format(motion))
                    self._frames.put(self._current_frame)
            except Exception, e:
                logging.error("Error in analysis: {}".format(e))
        logging.debug("Exiting vision capture thread")
        self._camera.close()

if __name__ == '__main__':
    global STOP
    STOP = False
    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_DEBUG)

    vision_results_queue = multiprocessing.Pipe()
    vision_worker = ImageAnalyzer(vision_results_queue, log_queue, logging.getLogger('').getEffectiveLevel())
    try:
        logging.debug("Starting image analysis")
        vision_worker.start()
        while not STOP:
            time.sleep(POLL_SECS)
    except Exception, e:
        logging.exception("Main exception {}".format(e))
    finally:
        logging.debug("Ending")
        vision_worker.stop()
        vision_worker.join()
        sys.exit(0)
