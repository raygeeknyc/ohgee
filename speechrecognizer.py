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

TEST_SUSPEND_SECS = 2.0
TEST_RESUME_SECS = 3.0

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
MAX_CONSECUTIVE_CONTINUOUS_STREAM_ERRORS = 3
# Google cloud speech can only stream 305 secs maxiumum, after 5 mins we recalibrate silence threshold
MAX_CONTINUOUS_STREAM_DUR_SECS = 304
  
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
        self.is_ready = multiprocessing.Event()
        self._training = multiprocessing.Event()
        self._transcript, _ = transcript
        self._stop_capturing = False
        self._stop_recognizing = False
        self._audio_buffer = None
        self._mic_stream = None
        self.is_ready.clear()
        self._trained_at = 0
        self._streamed_at = 0

    def suspendListening(self, training=False):
        logging.debug("TRACE suspendListening, training=%s", str(training))
        while training and self._suspend_listening.is_set():
            pass
        self._suspend_listening.set()
        if training:
            self._training.set()
        self.suspendRecognizing()

    def resumeListening(self):
        logging.debug("TRACE resumeListening")
        self._suspend_listening.clear()
        self.resumeRecognizing()

    def suspendRecognizing(self):
        logging.debug("TRACE suspendRecognizing")
        self._suspend_recognizing.set()

    def resumeRecognizing(self):
        logging.debug("TRACE resumeRecognizing")
        self._suspend_recognizing.clear()

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
            logging.debug("recognizer process active")
            self._audio_buffer = IterableQueue()
            self._audio = pyaudio.PyAudio()
            self._capturer = threading.Thread(target=self.captureSound)
            self._recognizer = threading.Thread(target=self.recognizeSpeech)
            self._recognizer.start()
            self._suspend_listening.clear()
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

    def trainSilence(self):
        logging.debug("Training silence")
        self._silence_threshold = 0
        silence_min = 9999
        silence_samples = 0
        while self._suspend_listening.is_set() and not self._training.is_set():
            pass
        self.suspendListening(training=True)
        for sample in range(SILENCE_TRAINING_SAMPLES):
            try:
                data = self._mic_stream.read(FRAMES_PER_BUFFER)
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
        self._silence_threshold = silence_min+(self._silence_threshold - silence_min)**0.5
        self._training.clear()
        self._trained_at = time.time()
        self.resumeListening()
        logging.info("Trained silence volume {} min was {} pause samples {} unpause_samples {}".format(self._silence_threshold, silence_min, PAUSE_LENGTH_IN_SAMPLES, UNPAUSE_LENGTH_IN_SAMPLES))

    def captureSound(self):
        logging.debug("Starting capturing")
        self._mic_stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        self.trainSilence()

        consecutive_silent_samples = PAUSE_LENGTH_IN_SAMPLES + 1
        consecutive_noisy_samples = 0
        samples = 0
 
        temp_audio_buffer = deque()

        is_suspended = self._suspend_listening.is_set()
        was_suspended = None
        paused = False
        self.is_ready.set()
        unpaused_at = 0

        while not self._stop_capturing:
            if was_suspended is None:
                was_suspended = not is_suspended
            else:
                was_suspended = is_suspended
            is_suspended = self._suspend_listening.is_set()
            if was_suspended != is_suspended:
                logging.debug("TRACE: capture suspended: %s", str(is_suspended))
 
            try:
                samples += 1
                logging.debug("TRACE reading audio")
                data = self._mic_stream.read(FRAMES_PER_BUFFER)
                if self._suspend_listening.is_set():
                    logging.debug("TRACE audio bypass")
                    continue
                volume = max(array.array('h', data))
                logging.debug("Volume max {}".format(volume))
                if volume > self._silence_threshold:
                    consecutive_noisy_samples += 1
                    consecutive_silent_samples = 0
                else:
                    consecutive_silent_samples += 1
                    consecutive_noisy_samples = 0
                
                if not paused and consecutive_silent_samples == PAUSE_LENGTH_IN_SAMPLES:
                    logging.debug("Pausing audio streaming after %f secs", time.time()-unpaused_at)
                    self.suspendRecognizing()
                    paused = True
                    paused_at = time.time()
                if paused:
                    if consecutive_noisy_samples == UNPAUSE_LENGTH_IN_SAMPLES: 
                        logging.debug("TRACE resuming audio streaming with %d chunks after %f secs", len(temp_audio_buffer), time.time()-paused_at)
                        paused = False
                        unpaused_at = time.time()
                        (self._audio_buffer.put(buffered_data) for buffered_data in temp_audio_buffer)
                        self.resumeRecognizing()
                    elif consecutive_noisy_samples == 0:
                        logging.debug("Clearing resumption buffer")
                        temp_audio_buffer.clear()
                    elif not self._suspend_listening.is_set():
                        logging.debug("Buffering possible resumption")
                        temp_audio_buffer.append(data)
               
                if not paused and not self._suspend_listening.is_set():
                    logging.debug("TRACE streaming chunk")
                    self._audio_buffer.put(data)
            except IOError:
                logging.exception("IOError capturing audio")
        logging.debug("ending sound capture")
        # stop Recording
        self._mic_stream.close()
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
        consecutive_continuous_stream_errors = 0
        while not self._stop_recognizing:
            logging.debug("Recognizing")
            try:
                if self._suspend_recognizing.is_set():
                    consecutive_continuous_stream_errors = 0
                    continue
                while self._audio_buffer.empty():
                    pass
                requests = (speech.StreamingRecognizeRequest(audio_content=sound_chunk) for sound_chunk in self._audio_buffer)
            
                self._streamed_at = time.time()
                logging.debug('created requests generator')
                responses = self._speech_client.streaming_recognize(streaming_config, requests)
                consecutive_continuous_stream_errors = 0
                for response in responses:
                    if not response.results:
                        continue
                    result = response.results[0]
                    if not result.alternatives:
                        continue
                    alternative = result.alternatives[0]
                    logging.info("TRACE speech: {}".format(alternative.transcript))
                    logging.debug("final: {}".format(result.is_final))
                    logging.debug("confidence: {}".format(alternative.confidence))
                    self._transcript.send(alternative.transcript)
                    if self._stop_recognizing:
                        break
            except Exception as e:
                logging.exception("error recognizing speech. Streaming for %s", str(time.time() - self._streamed_at))
                consecutive_continuous_stream_errors += 1
                if self._streamed_at and (time.time() - self._streamed_at > MAX_CONTINUOUS_STREAM_DUR_SECS):
                    logging.debug("TRACE maximum continuous sound was reached.")
                    logging.debug("Retraining silence threshold.")
                    self.is_ready.clear()
                    self.trainSilence()
                    self.is_ready.set()
                if consecutive_continuous_stream_errors > MAX_CONSECUTIVE_CONTINUOUS_STREAM_ERRORS:
                    logging.error("Maximum consecutive continuous stream errors exceeded, exiting")
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

    
    logging.debug("Waiting for speech recognizer to be ready")
    recognition_worker.is_ready.wait()
    for _ in range(2):
        print("listening for %d seconds" % TEST_RESUME_SECS)
        time.sleep(TEST_RESUME_SECS)
        print("pausing for %d seconds" % TEST_SUSPEND_SECS)
        recognition_worker.suspendListening()
        time.sleep(TEST_SUSPEND_SECS)
        recognition_worker.resumeListening()

    recognition_worker.stop()
    recognition_worker.join()

if __name__ == '__main__':
    print('running standalone recognizer')
    main(sys.argv)
    print('exiting')
