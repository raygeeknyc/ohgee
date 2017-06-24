import logging

import multiprocessing
from multiprocessingloghandler import ChildMultiProcessingLogHandler
import threading
from fedstream import FedStream
import pyaudio
import array
import Queue
import io
import os
import sys
from google.cloud import speech

# Setup audio and cloud speech
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAMES_PER_BUFFER = 2048
SILENCE_THRESHOLD = 700
PAUSE_LENGTH_SECS = 1
MAX_BUFFERED_SAMPLES = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)

class SpeechRecognizer(multiprocessing.Process):
    def __init__(self, transcript, log_queue, logging_level):
        multiprocessing.Process.__init__(self)
        self._log_queue = log_queue
        self._logging_level = logging_level
        self._exit = multiprocessing.Event()
        self._transcript, _ = transcript
        self._ingester = threading.Thread(target=self.getSound)
        self._processor = threading.Thread(target=self.processSound)
        self._stop_capturing = False
        self._stop_recognizing = False
        self._audio_buffer = Queue.Queue()

    def stop(self):
        logging.debug("***background received shutdown")
        self._exit.set()

    def _initLogging(self):
        handler = ChildMultiProcessingLogHandler(self._log_queue)
        logging.getLogger(str(os.getpid())).addHandler(handler)
        logging.getLogger(str(os.getpid())).setLevel(self._logging_level)

    def run(self):
        self._initLogging()
        try:
            self._audio_stream = FedStream(self._audio_buffer, self._log_queue, self._logging_level)
            self._audio = pyaudio.PyAudio()
            logging.debug("***background active")
            self._processor.start()
            self._ingester.start()
            self._exit.wait()
 
        except Exception, e:
            logging.exception("***background exception: {}".format(str(e)))
        logging.debug("***background terminating")
        self._stopCapturing()
        self._stopRecognizing()
        self._ingester.join()
        self._processor.join()

    def _stopCapturing(self):
        logging.debug("setting stop_capturing")
        self._stop_capturing = True
    
    def _stopRecognizing(self):
        logging.debug("setting stop_recognizing")
        self._stop_recognizing = True

    def getSound(self):
        logging.debug("starting capturing")
        mic_stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        consecutive_silent_samples = 0
        samples = 0
 
        while not self._stop_capturing:
            samples += 1
            volume = 0
            try:
                data = mic_stream.read(FRAMES_PER_BUFFER)
                volume = max(array.array('h', data))
                if volume <= SILENCE_THRESHOLD:
                    consecutive_silent_samples += 1
                else:
                    consecutive_silent_samples = 0
                logging.debug("mic read {} bytes".format(len(data)))
                self._audio_buffer.put(data)
                logging.debug("Vol: {}".format(volume))
            except IOError, e:
                logging.exception(e)

        logging.debug("ending sound capture")
        # stop Recording
        mic_stream.stop_stream()
        mic_stream.close()
        self._audio.terminate()
        logging.debug("stopped capturing")

    def processSound(self):
        logging.debug("started recognizing")
        self._speech_client = speech.Client()
        logging.debug("Starting sampling")
        audio_sample = self._speech_client.sample(
            stream=self._audio_stream,
            source_uri=None,
            encoding=speech.encoding.Encoding.LINEAR16,
            sample_rate_hertz=RATE)
        logging.debug("Starting recognizing")
        while not self._stop_recognizing:
            try:
                alternatives = audio_sample.streaming_recognize('en-US',
                    interim_results=True)
                for alternative in alternatives:
                    logging.debug("speech: {}".format(alternative.transcript))
                    logging.debug("final: {}".format(alternative.is_final))
                    logging.debug("confidence: {}".format(alternative.confidence))
                    if alternative.is_final or self._stop_recognizing:
                        self._transcript.send(alternative.transcript)
                    if self._stop_recognizing:
                        break
            except Exception, e:
                alternatives = None
                logging.exception("error recognizing speech: {}".format(str(e)))
        self._transcript.close()
        logging.debug("stopped recognizing")
