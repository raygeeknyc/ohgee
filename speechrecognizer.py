import logging

import multiprocessing
import time
from multiprocessingloghandler import ChildMultiProcessingLogHandler
import threading
from fedstream import FedStream
import pyaudio
import array
import Queue
import io
import os
import sys
import grpc  # for error types returned by the client
from google.cloud import speech

# Setup audio and cloud speech
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAMES_PER_BUFFER = 4096
PAUSE_LENGTH_SECS = 1.0
MAX_BUFFERED_SAMPLES = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)
SAMPLE_RETRY_DELAY_SECS = 0.1

# This is how many samples to take to find the lowest sound level
SILENCE_TRAINING_SAMPLES = 10

class SpeechRecognizer(multiprocessing.Process):
    def __init__(self, transcript, log_queue, logging_level):
        multiprocessing.Process.__init__(self)
        self._log_queue = log_queue
        self._logging_level = logging_level
        self._exit = multiprocessing.Event()
        self._suspend_listening = multiprocessing.Event()
        self._transcript, _ = transcript
        self._stop_capturing = False
        self._stop_recognizing = False
        self._audio_buffer = Queue.Queue()

    def resumeListening(self):
        logging.debug("***background received resume")
        self._suspend_listening.clear()

    def suspendListening(self):
        logging.debug("***background received suspend")
        self._suspend_listening.set()

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
            self._capturer = threading.Thread(target=self.captureSound)
            self._recognizer = threading.Thread(target=self.recognizeSpeech)
            self._audio_stream = FedStream(self._audio_buffer, self._log_queue, self._logging_level)
            self._audio = pyaudio.PyAudio()
            logging.debug("recognizer process active")
            self._recognizer.start()
            self._suspend_listening.clear()
            self._capturer.start()
            self._exit.wait()
        except Exception, e:
            logging.exception("recognizer process exception: {}".format(str(e)))
        finally:
            self._stopCapturing()
            self._stopRecognizing()
            self._capturer.join()
            self._recognizer.join()
            self._transcript.close()
            logging.debug("recognizer process terminating")
            sys.exit(0)

    def _stopCapturing(self):
        logging.debug("setting stop_capturing")
        self._stop_capturing = True
    
    def _stopRecognizing(self):
        logging.debug("setting stop_recognizing")
        self._stop_recognizing = True

    def trainSilence(self, mic_stream):
        logging.debug("Training silence")
        self._silence_threshold = 0
        silence_min = 9999
        silence_samples = 0
        for sample in xrange(SILENCE_TRAINING_SAMPLES):
            try:
                data = mic_stream.read(FRAMES_PER_BUFFER)
                volume = max(array.array('h', data))
                logging.debug("sample {}".format(volume))
                self._silence_threshold += volume
                silence_min = min(volume, silence_min)
                silence_samples += 1
            except Exception, e:
                logging.exception("Training mic read raised exception: {}".format(e))
        self._silence_threshold /= silence_samples
        self._silence_threshold -= (self._silence_threshold - silence_min)/2
        logging.info("Trained silence volume {} min was {} pause samples {}".format(self._silence_threshold, silence_min, PAUSE_LENGTH_IN_SAMPLES))

    def captureSound(self):
        logging.debug("starting capturing")
        mic_stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        self.trainSilence(mic_stream)
        consecutive_silent_samples = 999
        self._audio_stream.close()
        samples = 0
        while not self._stop_capturing:
            samples += 1
            volume = 0
            try:
                data = mic_stream.read(FRAMES_PER_BUFFER)
                if self._suspend_listening.is_set():
                    continue
                volume = max(array.array('h', data))
                logging.debug("Volume max {}".format(volume))
                if volume <= self._silence_threshold:
                    consecutive_silent_samples += 1
                else:
                    if consecutive_silent_samples >= PAUSE_LENGTH_IN_SAMPLES:
                        logging.debug("pause ended")
                        self._audio_stream.open()
                    consecutive_silent_samples = 0
                if consecutive_silent_samples == PAUSE_LENGTH_IN_SAMPLES:
                    logging.debug("pause started")
                    self._audio_stream.close()
                if consecutive_silent_samples < PAUSE_LENGTH_IN_SAMPLES:
                    self._audio_buffer.put(data)
            except IOError, e:
                logging.exception(e)
        logging.debug("ending sound capture")
        # stop Recording
        mic_stream.stop_stream()
        mic_stream.close()
        self._audio.terminate()
        logging.debug("stopped capturing")

    def recognizeSpeech(self):
        logging.debug("started recognizing")
        self._speech_client = speech.Client()
        logging.debug("Starting sampling")
        audio_sample = self._speech_client.sample(
            stream=self._audio_stream,
            source_uri=None,
            encoding=speech.encoding.Encoding.LINEAR16,
            sample_rate_hertz=RATE)
        logging.debug("Starting recognizing")
        waiting = False
        while not self._stop_recognizing:
            try:
                if self._audio_stream.closed:
                    if not waiting:
                        logging.debug("waiting for sound to analyze")
                        waiting = True
                    time.sleep(SAMPLE_RETRY_DELAY_SECS)
                    continue
                if waiting:
                    logging.debug("heard sound to analyze")
                    waiting = False
                alternatives = audio_sample.streaming_recognize('en-US',
                    interim_results=True)
                for alternative in alternatives:
                    logging.debug("speech: {}".format(alternative.transcript))
                    logging.debug("final: {}".format(alternative.is_final))
                    logging.debug("confidence: {}".format(alternative.confidence))
                    logging.debug("putting phrase {}".format(alternative.transcript))
                    if alternative.is_final or self._stop_recognizing:
                        self._transcript.send(alternative.transcript)
                    if self._stop_recognizing:
                        break
            except grpc._channel._Rendezvous, e:
                logging.debug("empty stream recognition attempted")
                continue
            except Exception, e:
                logging.exception("error recognizing speech: {}".format(e))
                continue
        logging.debug("stopped recognizing")
