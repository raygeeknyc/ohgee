VERSION_ID = ", , version twenty one"
import logging

# reorder as appropriate
_DEBUG = logging.DEBUG
_DEBUG = logging.INFO

import Tkinter
import PIL
from PIL import ImageTk, Image

import multiprocessing
from multiprocessingloghandler import ParentMultiProcessingLogHandler
import threading
import collections
import RPi.GPIO as GPIO
import time
import io
import sys
import os, signal
import Queue

import rgbled
import speechrecognizer
import phraseresponder
import speechanalyzer
import visionanalyzer
import imagesearch

global STOP
STOP = False

global waving
waving = False

DISPLAY_SLEEP_DELAY_SECS = 5 * 60
global mood_set_until
mood_set_until = 0
MOOD_SET_DURATION_SECS = 3
SEARCH_POLL_DELAY_SECS = 0.5
IMAGE_POLL_DELAY_SECS = 0.1
IMAGE_STICKY_DISPLAY_SECS = 3
IMAGE_MIN_DISPLAY_SECS = 0.2
LABEL_RESPONSE_DELAY_SECS = 60.0 * 10

INITIAL_WAKEUP_GREETING = ["I'm", "awake", VERSION_ID]

servoPin = 18
ARM_RELAXED_POSITION = 12.0
ARM_DOWN_POSITION = 9.0
ARM_UP_POSITION = 12.5
ARM_WAVE_LOWER_SECS = 0.5
ARM_WAVE_RAISE_SECS = 2
ARM_WAVE_DELAY_SECS = 1
MIN_FACE_WAVE_DELAY_SECS = 10

GREETING_INTERVAL_SECS = 5
SEARCH_INTERVAL_SECS = 10

SENTIMENT_DURATION_STIMULUS_FRAMES_THRESHOLD = 3
SENTIMENT_DURATION_STIMULUS_INCREMENT_FACTOR = 2.5

FACE_CLOSENESS_AREA_THRESHOLD = 1.0/10  # A face must be this portion of the frane for us to greet it
SPEECH_TMP_FILE="/tmp/speech.wav"
PICO_CMD='pico2wave -l en-US --wave "%s" "%s";aplay "%s"'
SCREEN_SLEEP_CMD='./screen_sleep.sh'
SCREEN_WAKE_CMD='./screen_wake.sh'

def getPhraseForSentiment(dominant_sentiment):
  if dominant_sentiment > 0:
    phrase,_ = visionanalyzer.getGoodMoodGreeting()
  elif dominant_sentiment < 0:
    phrase,_ = visionanalyzer.getBadMoodGreeting()
  else:
    phrase = None
  return phrase

def expireMood():
    global mood_set_until
    if mood_set_until and mood_set_until < time.time():
        mood_set_until = 0
        led.setColor(rgbled.OFF)

def setMoodTime():
    global mood_set_until
    global MOOD_SET_DURATION_SECS
    mood_set_until = time.time() + MOOD_SET_DURATION_SECS

def showGoodMood(score):
    logging.debug("Good mood {}".format(score))
    led.setColor(rgbled.GREEN)
    setMoodTime()

def showBadMood(score):
    logging.debug("Bad mood {}".format(score))
    led.setColor(rgbled.RED)
    setMoodTime()

def showMehMood(score):
    logging.debug("Meh mood {}".format(score))
    led.setColor(rgbled.CYAN)
    setMoodTime()

def signal_handler(sig, frame):
    global STOP
    logging.debug("INT signal trapped")
    if STOP:
        logging.debug("Second INT signal trapped, killing")
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        os.kill(os.getpid(), signal.SIGTERM)
    STOP = True
signal.signal(signal.SIGINT, signal_handler)
 
def speak(speech_queue):
    global STOP
    logging.debug("Speaker started")
    while not STOP:
        try:
            logging.debug("Waiting to talk")
            utterance = " ".join(speech_queue.get())
            recognition_worker.suspendListening()
            logging.debug("Saying {}".format(utterance))
            os.system(PICO_CMD % (SPEECH_TMP_FILE, utterance, SPEECH_TMP_FILE))
        except Exception, e:
            logging.exception("Error speaking")
        finally:
            recognition_worker.resumeListening()
    logging.debug("Speaker stopping")

def waveArm():
    raiseArm()
    time.sleep(ARM_WAVE_RAISE_SECS)
    lowerArm()
    time.sleep(ARM_WAVE_LOWER_SECS)
    relaxArm()
    time.sleep(0.5)
    arm.ChangeDutyCycle(0)

def wave():
    global waving
    global STOP
    while not STOP:
        while not waving:
            time.sleep(ARM_WAVE_DELAY_SECS)
        logging.debug("Wave")
        waveArm()
        waving = False

def receiveLanguageResults(nl_results, search_queue):
    logging.debug("Listening")
    _, nl_results = nl_results
    last_search_at = 0.0
    
    while True:
        try:
            phrase = nl_results.recv()
            text, tokens, entities, sentiment, decorated_noun = phrase
            logging.debug("Got spoken phrase {}".format(text))
            if speechanalyzer.isGood(sentiment):
                showGoodMood(sentiment.score)
            elif speechanalyzer.isBad(sentiment):
                showBadMood(sentiment.score)
            else:
                showMehMood(sentiment.score)
            response = phraseresponder.getResponse(text, entities)
            if response:
                logging.debug("Phrase matched")
                comeback, wave_flag = response
                speech_queue.put(comeback)
                if wave_flag:
                    startWaving()
            if decorated_noun:
                since_searched = time.time() - last_search_at
                if since_searched > SEARCH_INTERVAL_SECS:
                    search_queue.put(decorated_noun)
                    last_search_at = time.time()
        except EOFError:
            logging.debug("End of NL results queue")
            break
        except Exception, e:
            logging.exception("Error speaking")
    logging.debug("Done listening")

def watchForVisionResults(vision_results_queue, image_queue):
    logging.debug("Watching")
    _, vision_results_queue = vision_results_queue
    recent_sentiments = collections.deque([0.0, 0.0, 0.0], maxlen=3)
    recent_face_counts = collections.deque([0.0, 0.0, 0.0], maxlen=3)
    
    last_greeting_at = 0.0
    last_wave_at = 0l
    dominant_sentiment = -999
    last_label_response_at = time.time()
    prev_recognized_label_text = None
    while True:
        try:
            # Expire memory of the last image label we responded to
            if time.time() > (last_label_response_at + LABEL_RESPONSE_DELAY_SECS):
                prev_recognized_label_text = None
            greeting = None
            wave_flag = False
            feeling_good = False
            feeling_bad = False
            feeling_good_extended = False
            feeling_bad_extended = False
   
            processed_image_results = vision_results_queue.recv()
            processed_image, labels, faces, sentiment, area = processed_image_results
            logging.debug("{} faces detected".format(len(faces)))
            logging.debug("{} sentiment detected".format(sentiment))
            logging.debug("{} largest face".format(area))

            image_queue.put((processed_image, False))
            logging.debug("Put a processed image %s" % id(processed_image))

            if area >= FACE_CLOSENESS_AREA_THRESHOLD:
                if sentiment < 0: sentiment = -1
                if sentiment > 0: sentiment = 1
                face_count = len(faces)
            else:
                sentiment = 0
                face_count = 0
            recent_sentiments.appendleft(sentiment)
            recent_face_counts.appendleft(face_count)
               
            if recent_face_counts[0] == 0 and len(recent_face_counts) > 1 and recent_face_counts[1] > 0:
              logging.debug("Skipping one frame dropout of faces for sentiment tracking")
            else:
              if dominant_sentiment != sentiment:
                sentiment_duration = 0
            dominant_sentiment = sentiment
            sentiment_duration += 1

            if sentiment_duration == SENTIMENT_DURATION_STIMULUS_FRAMES_THRESHOLD:
              greeting = getPhraseForSentiment(dominant_sentiment)
              logging.debug("Got phrase {} for sentiment {}".format(greeting, dominant_sentiment))
              sentiment_reminder_delay = SENTIMENT_DURATION_STIMULUS_FRAMES_THRESHOLD
            elif sentiment_duration > SENTIMENT_DURATION_STIMULUS_FRAMES_THRESHOLD and ((sentiment_duration - SENTIMENT_DURATION_STIMULUS_FRAMES_THRESHOLD) %  sentiment_reminder_delay) == 0:
              greeting = getPhraseForSentiment(dominant_sentiment)
              logging.debug("Got additional phrase {} for sentiment {}".format(greeting, dominant_sentiment))
              sentiment_reminder_delay = int(SENTIMENT_DURATION_STIMULUS_INCREMENT_FACTOR * sentiment_reminder_delay)

            if recent_face_counts[0] > recent_face_counts[1] and recent_face_counts[0] > recent_face_counts[2]:
                logging.debug("Arrival")
                greeting = phraseresponder.getGreeting()
                wave_flag = True
            if recent_face_counts[0] < recent_face_counts[1] and recent_face_counts[0] < recent_face_counts[2] :
                logging.debug("Departure")
                greeting = phraseresponder.getFarewell()

            # Issue a response the first consecutive time we see a set of labels that we know a response to
            label_text = [label.description for label in labels]
            image_label_greeting = visionanalyzer.getGreetingForLabels(labels)
            if image_label_greeting and image_label_greeting[0]:
                logging.debug("l: {}  pl: {} g: {}".format(image_label_greeting[2], prev_recognized_label_text, image_label_greeting[0]))
                if image_label_greeting[2] == prev_recognized_label_text:
                    logging.debug("repeated greeting skipped")
                    image_label_greeting = None
                else:
                    prev_recognized_label_text = image_label_greeting[2]
                    last_label_response_at = time.time()
            if image_label_greeting:
                logging.debug("New greeting label matched")
                greeting, wave_flag, _ = image_label_greeting
  
            if greeting:
                if time.time() - last_greeting_at > GREETING_INTERVAL_SECS: 
                    last_greeting_at = time.time()
                    logging.debug("Greeting {} ({})".format(" ".join(greeting), len(greeting)))
                    speech_queue.put(greeting)
            if wave_flag:
                if time.time() - last_wave_at > MIN_FACE_WAVE_DELAY_SECS:
                    last_wave_at = time.time()
                    startWaving()

        except EOFError:
            logging.debug("End of vision queue")
            break
        except Exception, e:
            logging.exception("Error watching")
    logging.debug("Done watching")

def lowerArm():
    arm.ChangeDutyCycle(ARM_DOWN_POSITION)

def raiseArm():
    arm.ChangeDutyCycle(ARM_UP_POSITION)

def relaxArm():
    arm.ChangeDutyCycle(ARM_RELAXED_POSITION)

def startWaving():
    global waving
    if not waving:
        waving = True

def searchForTermImage(search_term):
    logging.debug("search for: {}".format(search_term))
    image = imagesearch.getTopImage(search_term)
    return image

def searchForObjects(search_queue, image_queue):
    logging.debug("search thread started")
    search_term = None
    while not STOP:
        try:
            t = search_queue.get(False)
            logging.debug("Search queue had an entry")
            search_term = t
        except Queue.Empty:
            if not search_term:
                logging.debug("Empty search queue, waiting")
                time.sleep(SEARCH_POLL_DELAY_SECS)
                continue
            logging.debug("Search term {}".format(search_term))
            top_image = searchForTermImage(search_term)
            if top_image:
                image_queue.put((top_image, True))
                logging.debug("Put image on display queue")
            search_term = None
        except Exception, e:
            logging.exception("error searching")
    logging.debug("done searching")

def sleepDisplay():
    try:
        os.system(SCREEN_SLEEP_CMD)
    except Exception, e:
        logging.exception("Error putting display to sleep")

def wakeDisplay():
    try:
        os.system(SCREEN_WAKE_CMD)
    except Exception, e:
        logging.exception("Error waking display from sleep")

def maintainDisplay(root_window, image_queue):
    last_image_at = time.time()
    display_off = False
    canvas = Tkinter.Canvas(root_window, width=root_window.winfo_screenwidth(), height=root_window.winfo_screenheight())
    canvas.pack()
    logged = False
    image = None
    tk_image = None
    skipped_images = 0
    while not STOP:
        try:
            try:
                show_image = False
                if (not display_off) and (time.time() - last_image_at > DISPLAY_SLEEP_DELAY_SECS):
                    display_off = True
                    sleepDisplay()
                t = image_queue.get(False)
                logging.debug("Image queue had an entry")
                image, sticky = t
                logging.debug("image %s" % id(image))
                if sticky:
                    logging.debug("got a sticky image")
                    show_image = True
                    image_display_min_secs = IMAGE_STICKY_DISPLAY_SECS
                else:
                    skipped_images += 1
            except Queue.Empty:
                if not image:
                    logging.debug("Empty image queue, waiting")
                    skipped_images = 0
                    time.sleep(IMAGE_POLL_DELAY_SECS)
                else:
                    skipped_images -= 1
                    show_image = True
                    image_display_min_secs = IMAGE_MIN_DISPLAY_SECS
                    logging.debug("got the most recent image, skipped over {} images".format(skipped_images))
            if show_image:
                if display_off:
                    wakeDisplay()
                    display_off = False
                last_image_at = time.time()
                logging.debug("displaying image %s" % id(image))
                buffer = io.BytesIO(image)
                buffer.seek(0)
                image = Image.open(buffer)
                image = image.resize((root_window.winfo_screenwidth(), root_window.winfo_screenheight()))
                prev_frame = tk_image
                tk_image = PIL.ImageTk.PhotoImage(image)
                canvas.create_image(0, 0, image=tk_image, anchor="nw")
                image = None
                logging.debug("displayed image %s" % id(image))
                time.sleep(image_display_min_secs)
        except Exception, e:
            if not logged:
                logging.exception("error displaying")
                logged = True
                continue
        finally:
            expireMood()
    logging.debug("Stopping image display")
    root_window.quit()
    
if __name__ == '__main__':
    root = Tkinter.Tk()
    #root.geometry("%dx%d+%d+%d" % (root.winfo_screenwidth(), root.winfo_screenheight(), 0, 0))
    root.wm_attributes('-fullscreen','true')
    root.wm_attributes('-type', 'splash')
    root.overrideredirect(True)
    root.config(cursor='none')

    led = rgbled.RgbLed(rgbled.redPin, rgbled.greenPin, rgbled.bluePin)
    led.setColor(rgbled.OFF)

    GPIO.setup(servoPin, GPIO.OUT)
    arm = GPIO.PWM(servoPin, 50)
    arm.start(0)

    waveArm()

    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_DEBUG)

    transcript = multiprocessing.Pipe()
    recognition_worker = speechrecognizer.SpeechRecognizer(transcript, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting speech recognition")
    recognition_worker.start()
    unused, _ = transcript
    unused.close()

    nl_results = multiprocessing.Pipe()
    analysis_worker = speechanalyzer.SpeechAnalyzer(transcript, nl_results, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting speech analysis")
    analysis_worker.start()
    unused, _ = nl_results
    unused.close()

    vision_results_queue = multiprocessing.Pipe()
    vision_worker = visionanalyzer.ImageAnalyzer(vision_results_queue, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting image analysis")
    vision_worker.start()
    unused, _ = vision_results_queue
    unused.close()

    try:
        waver = threading.Thread(target = wave, args=())
        waver.start()

        image_queue = Queue.Queue()
        watcher = threading.Thread(target = watchForVisionResults, args=(vision_results_queue, image_queue))
        watcher.start()

        search_queue = Queue.Queue()
        searcher = threading.Thread(target = searchForObjects, args=(search_queue, image_queue,))
        searcher.start()

        displayer = threading.Thread(target = maintainDisplay, args=(root, image_queue,))
        displayer.start()

        speech_queue = Queue.Queue()
        speaker = threading.Thread(target = speak, args=(speech_queue,))
        speaker.start()
        
        listener = threading.Thread(target = receiveLanguageResults, args=(nl_results, search_queue,))
        listener.start()

        speech_queue.put(INITIAL_WAKEUP_GREETING)
        logging.debug("Waiting")
        root.mainloop()
    except Exception, e:
        logging.error("Error in main: {}".format(e))
    finally:
        logging.debug("Ending main")
        vision_worker.stop()
        recognition_worker.stop()
        analysis_worker.stop()
        logging.debug("Waiting for background processes to exit")
        logging.debug("wait for vision")
        vision_worker.join()
        logging.debug("wait for recognition to exit")
        recognition_worker.join()
        logging.debug("wait for analysis to exit")
        analysis_worker.join()
        led.setColor(rgbled.OFF)
        arm.stop()
        GPIO.cleanup()
        logging.debug("Done")
        sys.exit(0)
