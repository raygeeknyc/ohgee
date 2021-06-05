#!/usr/bin/python3

import logging
_LOGGING_LEVEL = logging.DEBUG

import multiprocessing
import time
from multiprocessingloghandler import ParentMultiProcessingLogHandler, ChildMultiProcessingLogHandler
import threading
from collections import deque
from fedstream import FedStream
from google.cloud import speech
import pyaudio
import array
import queue
import io
import os
import sys

# Setup audio and cloud speech
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAMES_PER_BUFFER = 1600
PAUSE_LENGTH_SECS = 0.5
UNPAUSE_LENGTH_SECS = 0.2
MAX_BUFFERED_SAMPLES = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)
UNPAUSE_LENGTH_IN_SAMPLES = int((UNPAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)
SAMPLE_RETRY_DELAY_SECS = 0.1

# This is how many samples to take to find the lowest sound level
SILENCE_TRAINING_SAMPLES = 10
MAX_CONSECUTIVE_ERRORS = 3
  
class IterableQueue(queue.SimpleQueue): 
    _sentinel = object()
    def __iter__(self):
        return iter(self.get, self._sentinel)

    def close(self):
        self.put(self._sentinel)

class SpeechRecognizer(multiprocessing.Process):
    def __init__(self, transcript, log_queue, logging_level):
        multiprocessing.Process.__init__(self)
        self._log_queue = log_queue
        self._logging_level = logging_level
        self._exit = multiprocessing.Event()
        self._suspend_listening = multiprocessing.Event()
        self._suspend_recognizing = multiprocessing.Event()
        self._transcript, _ = transcript
        self._stop_capturing = False
        self._stop_recognizing = False
        self._audio_buffer = IterableQueue()

    def resumeListening(self):
        logging.debug("resumeListening")
        self._suspend_listening.clear()
        self.resumeRecognizing()

    def suspendListening(self):
        logging.debug("suspendListening")
        self._suspend_listening.set()
        self.suspendRecognizing()

    def resumeRecognizing(self):
        logging.debug("resumeRecognizing")
        self._suspend_recognizing.clear()

    def suspendRecognizing(self):
        logging.debug("suspendRecognizing")
        self._suspend_recognizing.set()

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
            self._audio = pyaudio.PyAudio()
            logging.debug("recognizer process active")
            self._recognizer.start()
            self._suspend_listening.clear()
            self._suspend_recognizing.clear()
            self._capturer.start()
            self._exit.wait()
        except Exception:
            logging.exception("recognizer process exception")
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
        for sample in range(SILENCE_TRAINING_SAMPLES):
            try:
                data = mic_stream.read(FRAMES_PER_BUFFER)
                volume = max(array.array('h', data))
                logging.debug("sample {}".format(volume))
                if volume < 0:
                    continue
                self._silence_threshold += volume
                silence_min = min(volume, silence_min)
                silence_samples += 1
            except Exception:
                logging.exception("Training mic read raised exception")
        self._silence_threshold /= silence_samples
        self._silence_threshold -= abs(self._silence_threshold - silence_min)/4
        logging.info("Trained silence volume {} min was {} pause samples {} unpause_samples {}".format(self._silence_threshold, silence_min, PAUSE_LENGTH_IN_SAMPLES, UNPAUSE_LENGTH_IN_SAMPLES))

    def captureSound(self):
        logging.debug("starting capturing")
        mic_stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        self.trainSilence(mic_stream)
        consecutive_silent_samples = PAUSE_LENGTH_IN_SAMPLES + 1
        consecutive_noisy_samples = 0
        samples = 0
        paused_for_silence = True
 
        temp_audio_buffer = deque()
        while not self._stop_capturing:
            if self._suspend_listening.is_set():
                continue
            try:
                samples += 1
                data = mic_stream.read(FRAMES_PER_BUFFER)
                volume = max(array.array('h', data))
                logging.debug("Volume max {}".format(volume))
                if volume > self._silence_threshold:
                    consecutive_noisy_samples += 1
                    consecutive_silent_samples = 0
                else:
                    consecutive_silent_samples += 1
                    consecutive_noisy_samples = 0
                
                if not paused_for_silence and consecutive_silent_samples == PAUSE_LENGTH_IN_SAMPLES:
                    logging.debug("Pausing audio streaming")
                    self.suspendRecognizing()
                    paused_for_silence = True
                if paused_for_silence:
                    if consecutive_noisy_samples == UNPAUSE_LENGTH_IN_SAMPLES: 
                        logging.debug("Resuming audio streaming")
                        paused_for_silence = False
                        (self._audio_buffer.put(buffered_data) for buffered_data in temp_audio_buffer)
                        self.resumeRecognizing()
                    elif consecutive_noisy_samples == 0:
                        logging.debug("Clearing resumption buffer")
                        temp_audio_buffer.clear()
                    else:
                        logging.debug("Buffering possible resumption")
                        temp_audio_buffer.append(data)
               
                if not paused_for_silence:
                    self._audio_buffer.put(data)
            except IOError:
                logging.exception("IOError capturing audio")
        logging.debug("ending sound capture")
        # stop Recording
        mic_stream.stop_stream()
        mic_stream.close()
        self._audio.terminate()
        logging.debug("stopped capturing")

    def recognizeSpeech(self):
        logging.debug("started recognizing")
        self._speech_client = speech.SpeechClient()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code="en-US",
        )
        streaming_config = speech.StreamingRecognitionConfig(config=config,
            interim_results=False)

        logging.debug("Starting recognizing")
        consecutive_recognition_errors = 0
        while not self._stop_recognizing:
            try:
                if self._suspend_recognizing.is_set():
                    continue
                requests = (speech.StreamingRecognizeRequest(audio_content=sound_chunk) for sound_chunk in self._audio_buffer)
                logging.debug('created requests generator')
                responses = self._speech_client.streaming_recognize(streaming_config, requests)
                for response in responses:
                    if not response.results:
                        continue
                    result = response.results[0]
                    if not result.alternatives:
                        continue
                    alternative = result.alternatives[0]
                    logging.info("speech: {}".format(alternative.transcript))
                    logging.debug("final: {}".format(result.is_final))
                    logging.debug("confidence: {}".format(alternative.confidence))
                    self._transcript.send(alternative.transcript)
                    if self._stop_recognizing:
                        break
                    consecutive_recognition_errors = 0
            except Exception as e:
                logging.exception("error recognizing speech")
                consecutive_recognition_errors += 1
                if consecutive_recognition_errors > MAX_CONSECUTIVE_ERRORS:
                    logging.error("Maximum consecutive errors exceeded, exiting")
                    raise e
                continue
        logging.debug("stopped recognizing")

def main(unused):
    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_LOGGING_LEVEL)

    transcript = multiprocessing.Pipe()
    recognition_worker = SpeechRecognizer(transcript, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting speech recognition")
    recognition_worker.start()
    unused, _ = transcript
    unused.close()

if __name__ == '__main__':
    print('running standalone recognizer')
    main(sys.argv)
    print('exiting')
