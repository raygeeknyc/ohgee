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
from random import randint
import io
import sys
import os
import time
import signal
import Queue
import threading

# This is the desired resolution of the Pi camera
RESOLUTION = (320, 240)
CAPTURE_RATE_FPS = 4
# This is over an observed covered camera's noise
TRAINING_SAMPLES = 5
# This is how much the green channel has to change to consider a pixel changed
PIXEL_SHIFT_SENSITIVITY = 30

# This is how long to sleep in various threads between shutdown checks
POLL_SECS = 0.5

# This is the rate at which to send frame to the vision service
ANALYSIS_RATE_FPS = 1.0/2
_ANALYSIS_DELAY_SECS = 1.0/ANALYSIS_RATE_FPS

def signal_handler(sig, frame):
    global STOP
    if STOP:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    logging.debug("SIGINT")
    STOP = True
signal.signal(signal.SIGINT, signal_handler)

DOG_LABELS = ["dog", "canine"]
DOG_GREETINGS = (["here", "doggie"], ["hi","puppy"],  ["hello", "puppy"], ["woof", "woof"], ["bark"], ["good", "puppy"], ["nice", "doggie"])

CAT_LABELS = ["cat", "feline"]
CAT_GREETINGS = (["meow"], ["meow", "meow"], ["nice", "kitty"])

EYEGLASS_LABELS = ["glasses", "eyewear"]
EYEGLASS_GREETINGS = (["those", "are", "nice", "eyeglasses"], ["I", "like", "your", "glasses"], ["nice", "glasses"], [], [], [])

# Only first first label found in tags will be used, so prioritize them in this list
LABELS_GREETINGS = [(DOG_LABELS, DOG_GREETINGS, True),
  (CAT_LABELS, CAT_GREETINGS, False),
  (EYEGLASS_LABELS, EYEGLASS_GREETINGS, False)]

def randomGreetingFrom(phrases):
    if not phrases: return []
    return phrases[randint(0,len(phrases)-1)]

def getGreeting(labels):
    for tags, greetings, wave_flag in LABELS_GREETINGS:
        if labelMatch(labels, tags):
            return (randomGreetingFrom(greetings), wave_flag)
    return None

def labelMatch(labels,tags):
    for candidate_label in labels:
        if candidate_label.description in tags:	
            return candidate_label
    return None

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
        self._last_analysis_at = 0.0
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
        image_pixels = image.load()
        self._image_buffer.seek(0)
        image = self._image_buffer.getvalue()
        self._last_frame_at = time.time()
        return (image, image_pixels)

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
                if abs(self._current_frame[1][x,y][1] - self._prev_frame[1][x,y][1]) > PIXEL_SHIFT_SENSITIVITY:
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
        self._vision_client = vision.Client()
        while not self._stop_analyzing:
            frame = None
            while (self._last_analysis_at + _ANALYSIS_DELAY_SECS) > time.time() and not self._stop_analyzing:
                time.sleep(POLL_SECS)
            self._last_analysis_at = time.time()
            while True and not self._stop_analyzing:
                try:
                    f = self._frames.get(block=False)
                    frame = f
                except Queue.Empty:
                    break
            if frame:
                logging.debug("Trailing frame read")
                results = self._analyzeFrame(frame)
                self._vision_queue.send(results)
            else:
                logging.debug("No frame in queue")
        self._vision_queue.close()
        logging.debug("Exiting vision analyze thread")

    def _analyzeFrame(self, frame):
        remote_image = self._vision_client.image(content=frame[0])
        labels = remote_image.detect_labels()
        faces = remote_image.detect_faces(limit=5)
        return (frame[0], labels, faces)

    def captureFrames(self):
        self._image_buffer = io.BytesIO()
        self._camera = PiCamera()
        self._camera.resolution = RESOLUTION
        self._camera.vflip = True
        prev_array = None
        logging.info("Training motion detection")
        self.trainMotion()
        logging.info("Trained motion detection {}".format(self._motion_threshold))
        while not self._stop_capturing:
            try:
                self.getNextFrame()
                motion = self.calculateImageDifference()
                if motion > self._motion_threshold:
                    logging.debug("motion={}".format(motion))
                    self._frames.put(self._current_frame)
            except Exception, e:
                logging.error("Error in analysis: {}".format(e))
        logging.debug("Exiting vision capture thread")
        self._camera.close()

def watchForResults(vision_results_queue):
    global STOP

    _, incoming_results = vision_results_queue
    try:
        while True:
            processed_image_results = incoming_results.recv()
            image, labels, faces = processed_image_results
            logging.debug("{} faces detected".format(len(faces)))
            for label in labels:
                logging.debug("label: {}".format(label.description))
    except EOFError:
        logging.debug("Done watching")

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
        unused, _ = vision_results_queue
        unused.close()
        watcher = threading.Thread(target = watchForResults, args=(vision_results_queue,))
        watcher.start()
        while not STOP:
            time.sleep(POLL_SECS)
    except Exception, e:
        logging.exception("Main exception {}".format(e))
    finally:
        logging.debug("Ending")
        vision_worker.stop()
        vision_worker.join()
        logging.debug("background process returned, exiting main process")
        sys.exit(0)
