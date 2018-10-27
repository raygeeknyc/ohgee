import logging
# Used only if this is run as main
_DEBUG = logging.DEBUG

SENTIMENT_CONFIDENCE_THRESHOLD = 0.25
GOOD_SENTIMENT_THRESHOLD = SENTIMENT_CONFIDENCE_THRESHOLD
BAD_SENTIMENT_THRESHOLD = -1*SENTIMENT_CONFIDENCE_THRESHOLD

# Import the packages we need for drawing and displaying images
from PIL import Image, ImageDraw

# Imports the Google Cloud client packages we need
from google.cloud import vision
from google.cloud.vision.likelihood import Likelihood

from picamera import PiCamera

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
RESOLUTION = (600, 400)
CAPTURE_RATE_FPS = 2
# This is over an observed covered camera's noise
TRAINING_SAMPLES = 5
# This is how much the green channel has to change to consider a pixel changed
PIXEL_SHIFT_SENSITIVITY = 30
# This is the portion of pixels to compare when detecting motion
MOTION_DETECT_SAMPLE = 1.0/20  # so... 5%? (Kudos to Sarah Cooper)

# This is how long to sleep in various threads between shutdown checks
POLL_SECS = 0.1

# This is the rate at which to send frames to the vision service
ANALYSIS_RATE_FPS = 1
_ANALYSIS_DELAY_SECS = 1.0/ANALYSIS_RATE_FPS

COLOR_MEH = (0, 0, 127)
COLOR_BAD = (200, 0, 0)
COLOR_GOOD = (0, 200, 0)
COLOR_FEATURES = (255,255,255)

def signal_handler(sig, frame):
    global STOP
    if STOP:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    logging.debug("SIGINT")
    STOP = True
signal.signal(signal.SIGINT, signal_handler)

EMPTY_LABELS = []

BAD_MOOD_GREETINGS = (["don't", "worry", "be", "happy"], ["I'm", "sorry", "that", "you're", "not", "feeling", "happy"], ["You", "look", "down"], ["I", "hope", "that", "I", "can", "cheer", "you", "up"], ["I", "hope", "that", "you", "feel", "better", "soon"], ["Smile!"])

GOOD_MOOD_GREETINGS = (["I'm", "glad", "that", "you", "are", "happy"], ["You", "look", "happy"], ["You", "cheer", "me", "up"], ["It's", "great", "to", "see", "you", "happy"], ["Great", "day"])

DOG_LABELS = ["dog", "canine"]
DOG_GREETINGS = (["here", "doggie"], ["hi","puppy"],  ["hello", "puppy"], ["woof", "woof"], ["bark", "bark"], ["good", "puppy"], ["good", "puppy"], ["nice", "doggie"])

CAT_LABELS = ["cat", "feline"]
CAT_GREETINGS = (["meow"], ["meow", "meow"], ["nice", "kitty"], ["what", "a", "nice", "cat"])

HAT_LABELS = ["hat", "cap", "headgear"]
HAT_GREETINGS = (["that's", "a", "nice", "hat"], ["nice", "hat"], ["nice", "cap"], ["I", "like", "your", "hat"])

COFFEE_LABELS = ["espresso", "cup", "mug", "coffee", "coffee cup", "drinkware"]
COFFEE_GREETINGS = (["is", "that", "a", "cup", "of", "good", "coffee"], ["I", "love", "coffee", "too"], ["I", "hope", "that", "you", "enjoy", "your", "coffee"])

EYEGLASS_LABELS = ["glasses", "eyewear"]
EYEGLASS_GREETINGS = (["those", "are", "nice", "eye", "glasses"], ["I", "like", "your", "glasses"], ["nice", "glasses"], ["nice", "eye", "glasses"], [], [], [], [])

FLOWER_LABELS = ["flowers", "flower", "floral"]
FLOWER_GREETINGS = (["what", "a", "pretty", "flower"], ["nice", "flowers"], [])

# Only the first label found in tags will be used, so prioritize them in this list
LABELS_GREETINGS = [(DOG_LABELS, DOG_GREETINGS, EMPTY_LABELS, True),
  (CAT_LABELS, CAT_GREETINGS, EMPTY_LABELS, False),
  (HAT_LABELS, HAT_GREETINGS, EMPTY_LABELS, False),
  (FLOWER_LABELS, FLOWER_GREETINGS, EMPTY_LABELS, False),
  (COFFEE_LABELS, COFFEE_GREETINGS, EMPTY_LABELS, False),
  (EYEGLASS_LABELS, EYEGLASS_GREETINGS, EMPTY_LABELS, False)]

def randomGreetingFrom(phrases):
    if not phrases: return []
    return phrases[randint(0,len(phrases)-1)]

def getBadMoodGreeting():
    return (randomGreetingFrom(BAD_MOOD_GREETINGS), False)

def getGoodMoodGreeting():
    return (randomGreetingFrom(GOOD_MOOD_GREETINGS), False)

# Return the first label of the set that a match was found in
# but a match was not found in excludes
def getGreetingForLabels(labels):
    for tags, greetings, excludes, wave_flag in LABELS_GREETINGS:
        for label in labels:
            logging.debug("label: {}".format(label.description))
        matched_label_text = labelMatch(labels, tags)
        if matched_label_text:
            matched_exclude = labelMatch(labels, excludes)
            if not matched_exclude:
                return (randomGreetingFrom(greetings), wave_flag, tags[0])
    return None

def labelMatch(labels,tags):
    for candidate_label in labels:
        if candidate_label.description in tags:	
            return candidate_label.description
    return None

# Sentiment is -1, 0 or +1 for this sentiment and level
# -1 == bad, 0 == meh, +1 == good
def getSentimentForLevel(face, level):
    if face.joy == level or face.surprise == level:
        logging.debug("getSentimentForLevel: %s joy: %s surprise: %s" % (str(level), str(face.joy), str(face.surprise)))
        return 1.0
    if face.anger == level or face.sorrow == level:
        logging.debug("getSentimentForLevel: %s anger: %s sorrow: %s" % (str(level), str(face.anger), str(face.sorrow)))
        return -1.0
    return 0.0

def getSentimentWeightedByLevel(face):
    logging.debug("joy: {}, surprise:{}, anger:{}, sorrow:{}".format(
        face.joy, face.surprise, face.anger, face.sorrow))
    sentiment = getSentimentForLevel(face, Likelihood.VERY_LIKELY)
    if sentiment != 0:
       return sentiment
    sentiment = getSentimentForLevel(face, Likelihood.LIKELY)
    if sentiment != 0:
       return sentiment * SENTIMENT_CONFIDENCE_THRESHOLD
    sentiment = getSentimentForLevel(face, Likelihood.POSSIBLE)
    if sentiment != 0:
       return sentiment * SENTIMENT_CONFIDENCE_THRESHOLD
    sentiment = getSentimentForLevel(face, Likelihood.UNLIKELY)
    if sentiment != 0:
       return sentiment * 0.25
    return 0.0

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
        s=time.time()
        self._image_buffer.seek(0)
        self._camera.capture(self._image_buffer, format="jpeg", use_video_port=True)
        self._image_buffer.seek(0)
        image = Image.open(self._image_buffer)
        image_pixels = image.load()
        image = self._image_buffer.getvalue()
        self._last_frame_at = time.time()
        logging.debug("capturePilFrame took {}".format(time.time()-s))
        return (image, image_pixels)

    def getNextFrame(self):
        delay = (self._last_frame_at + self._frame_delay_secs) - time.time()
        if delay > 0:
            time.sleep(delay)
        self._current_frame = self.capturePilFrame()

    def calculateImageDifference(self, change_threshold=None, sample_percentage=MOTION_DETECT_SAMPLE):
        """
        Detect changes in the green channel.
        Sample sample_percentage of pixels, evenly distributed throughout
        the image's pixel map.
        If change_threshold is specified, exit once it's reached.
        """
        
        s = time.time()
        changed_pixels = 0
        sample_size = sample_percentage * self._camera.resolution[0] * self._camera.resolution[1] 
        step_size = self._camera.resolution[0] * self._camera.resolution[1] / sample_size
        # We choose the "most square" sampling interval to avoid sampling one or few stripes
        if self._camera.resolution[0] < self._camera.resolution[1]:
            y_step = int(sample_size / self._camera.resolution[0])
            x_step = 1
        else:
            x_step = int(sample_size / self._camera.resolution[0])
            y_step = 1
        logging.debug("Motion threshold, pct, size, step_size, x_step, y_step: {},{},{},{},{},{}".format(change_threshold, sample_percentage, sample_size, step_size, x_step, y_step))
        samples = 0
        for x in xrange(0, self._camera.resolution[0], x_step):
            for y in xrange(0, self._camera.resolution[1], y_step):
                samples += 1
                if abs(self._current_frame[1][x,y][1] - self._prev_frame[1][x,y][1]) > PIXEL_SHIFT_SENSITIVITY:
                    changed_pixels += 1
                    if change_threshold and changed_pixels > change_threshold:
                        logging.debug("reached threshold: {}, {} secs".format(changed_pixels, time.time()-s))
                        return changed_pixels 
        logging.debug("calculated change: {}, {} secs".format(changed_pixels, time.time()-s))
        return changed_pixels

    def imageDifferenceOverThreshold(self, changed_pixels_threshold):
        "Are there more changed pixels than we've established as a lower bound for motion?"
        changed_pixels = self.calculateImageDifference(changed_pixels_threshold)
        return changed_pixels > changed_pixels_threshold

    def trainMotion(self):
        logging.debug("Training motion")
        trained = False
        try:
            self._camera.start_preview(fullscreen=False, window=(100,100,self._camera.resolution[0], self._camera.resolution[1]))
            self._motion_threshold = 9999
            self.getNextFrame()
            for i in range(TRAINING_SAMPLES):
                self._prev_frame = self._current_frame
                self.getNextFrame()
                motion = self.calculateImageDifference()
                self._motion_threshold = min(motion, self._motion_threshold)
            trained = True
        finally:
            self._camera.stop_preview()
        logging.debug("Trained {}".format(trained))
        return trained

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
            logging.exception("Error in vision main thread")
        finally:
            logging.debug("Exiting vision")
            sys.exit(0)

    def analyzeVision(self):
        self._vision_client = vision.Client()
        skipped_images = 0
        frame = None
        while not self._stop_analyzing:
            try:
                frame = self._frames.get(block=False)
                skipped_images += 1
            except Queue.Empty:
                if not frame:
                    logging.debug("Empty image queue, waiting")
                    skipped_images = 0
                    time.sleep(POLL_SECS)
                else:
                    skipped_images -= 1
                    logging.debug("Trailing frame read, skipped {} frames".format(skipped_images))
                    try:
                        results = self._analyzeFrame(frame)
                        buffer = io.BytesIO()
                        results[0].save(buffer, format="JPEG")
                        buffer.seek(0)
                        img_bytes = buffer.getvalue()
                        logging.debug("send image %s" % id(img_bytes))
                        self._vision_queue.send((img_bytes, results[1], results[2], results[3], results[4]))
                    except Exception, e:
                        logging.exception("error reading image")
                    finally:
                        frame = None
        self._vision_queue.close()
        logging.debug("Exiting vision analyze thread")

    def _analyzeFrame(self, frame):
        s=time.time()
        logging.debug("analyzing image")
        remote_image = self._vision_client.image(content=frame[0])
        labels = remote_image.detect_labels()
        faces = remote_image.detect_faces(limit=5)
        faces_details = findFacesDetails(faces)
        im = Image.open(io.BytesIO(frame[0]))
        size = im.size[0] * im.size[1]
        canvas = ImageDraw.Draw(im)
        obscureFacesWithSentiments(canvas, faces_details)

        strongest_sentiment = 0.0
        max_confidence = 0.0
        max_area = 0.0
        for face_detail in faces_details:
            if face_detail[3] > max_area:
                max_area = face_detail[3]
            if face_detail[2] > max_confidence:
                max_confidence = face_detail[2]
                strongest_sentiment = face_detail[0]
                logging.debug("sentiment:{}".format(strongest_sentiment))
        logging.debug("_analyzeFrame took {}".format(time.time()-s))
        max_area_portion = (max_area * 1.0) / size
        return (im, labels, faces, strongest_sentiment, max_area_portion)

    def captureFrames(self):
        self._image_buffer = io.BytesIO()
        self._camera = PiCamera()
        self._camera.resolution = RESOLUTION
        self._camera.vflip = True
        prev_array = None
        logging.info("Training motion detection")
        for retry in xrange(3):
            if self.trainMotion():
                break
        logging.info("Trained motion detection {}".format(self._motion_threshold))
        while not self._stop_capturing:
            try:
                self.getNextFrame()
                if self.imageDifferenceOverThreshold(self._motion_threshold):
                    logging.debug("Motion detected")
                    self._frames.put(self._current_frame)
                    self._prev_frame = self._current_frame
                    self.getNextFrame()
            except Exception, e:
                logging.error("Error in analysis: {}".format(e))
        logging.debug("Exiting vision capture thread")
        self._camera.close()

def findFacesDetails(faces):
    face_details = []
    if faces:
        for face in faces:
            top = 9999
            left = 9999
            bottom = 0
            right = 0
            for point in face.bounds.vertices:
                top = min(top, point.y_coordinate)
                left = min(left, point.x_coordinate)
                bottom = max(bottom, point.y_coordinate)
                right = max(right, point.x_coordinate)
            sentiment = getSentimentWeightedByLevel(face)
            area = abs(bottom - top) * abs(right - left)
            face_details.append((sentiment, ((left, top), (right, bottom)), face.detection_confidence, area))
    return face_details

def getColorForSentiment(sentiment):
    if sentiment < 0:
        return COLOR_BAD
    if sentiment > 0:
        return COLOR_GOOD
    return COLOR_MEH

def watchForResults(vision_results_queue):
    global STOP

    _, incoming_results = vision_results_queue
    try:
        while True:
            image, labels, faces = incoming_results.recv()
            logging.debug("{} faces detected".format(len(faces)))
            for label in labels:
                logging.debug("label: {}".format(label.description))
    except EOFError:
        logging.debug("Done watching")

def obscureFacesWithSentiments(canvas, face_details):
   for face_sentiment, face_boundary, _, _ in face_details:
        sentiment_color = getColorForSentiment(face_sentiment)
        canvas.ellipse(face_boundary, fill=sentiment_color, outline=None)
        eye_size = max(1, (face_boundary[1][0] - face_boundary[0][0]) / 50)
        nose_size = 2*eye_size
        eye_level = face_boundary[0][1] + (face_boundary[1][1] - face_boundary[0][1])/3.0
        nose_level = face_boundary[0][1] + (face_boundary[1][1] - face_boundary[0][1])/2.0
        mouth_size_h = (face_boundary[1][0] - face_boundary[0][0])/2.0
        mouth_size_v = (face_boundary[1][1] - nose_level)/2.0
        mouth_size = min(mouth_size_v, mouth_size_h)
        mouth_inset = ((face_boundary[1][0]-face_boundary[0][0])-mouth_size)/2
        canvas.ellipse((face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/3.0)-eye_size, eye_level-eye_size, face_boundary[0][0]+((face_boundary[1][0]-face_boundary[0][0])/3.0)+eye_size, eye_level + eye_size), None, outline=COLOR_FEATURES)
        canvas.ellipse((face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/3.0)*2-eye_size, eye_level-eye_size, face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/3.0)*2+eye_size, eye_level+eye_size), None, outline=COLOR_FEATURES)

        canvas.ellipse((face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/2.0)-nose_size, nose_level-nose_size, face_boundary[0][0]+((face_boundary[1][0] - face_boundary[0][0])/2.0)+nose_size, nose_level+nose_size), outline=COLOR_FEATURES, fill=COLOR_FEATURES)

        if sentiment_color == COLOR_GOOD:
            canvas.chord(( face_boundary[0][0]+mouth_inset, nose_level, face_boundary[0][0]+mouth_inset+mouth_size, nose_level+mouth_size), 35, 135, fill=COLOR_FEATURES, outline=COLOR_FEATURES)
        elif sentiment_color == COLOR_BAD:
            canvas.chord(( face_boundary[0][0]+mouth_inset, face_boundary[1][1]-(face_boundary[1][1]-nose_level)*0.67, face_boundary[0][0]+mouth_inset+mouth_size, face_boundary[1][1]), 215, 335, fill=COLOR_FEATURES, outline=COLOR_FEATURES)

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
        logging.exception("Main exception")
    finally:
        logging.debug("Ending")
        vision_worker.stop()
        vision_worker.join()
        logging.debug("background process returned, exiting main process")
        sys.exit(0)
