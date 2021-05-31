#!/usr/bin/python3

import logging
_DEBUG = logging.DEBUG

from google.cloud import speech
import multiprocessing
import multiprocessingloghandler
import time
import multiprocessing
import microphonestream
import threading
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
FRAMES_PER_BUFFER = 4096
PAUSE_LENGTH_SECS = 1.0
MAX_BUFFERED_SAMPLES = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)
SAMPLE_RETRY_DELAY_SECS = 0.1

# This is how many samples to take to find the lowest sound level
SILENCE_TRAINING_SAMPLES = 10

# How many consecutive errors we'll tolerate from the cloud speech service
MAX_CONSECUTIVE_SPEECH_ERRORS = 3

class SpeechRecognizer(multiprocessing.Process):
    def __init__(self, transcript, log_queue, logging_level):
        super(SpeechRecognizer,self).__init__()
        self._log_queue = log_queue
        self._logging_level = logging_level
        self._exit = multiprocessing.Event()
        self._suspend_listening = multiprocessing.Event()
        self._transcript, _ = transcript
        self._stop_capturing = False
        self._stop_recognizing = False
        self._audio_generator = None

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
        handler = multiprocessingloghandler.ChildMultiProcessingLogHandler(self._log_queue)
        logging.getLogger(str(os.getpid())).addHandler(handler)
        logging.getLogger(str(os.getpid())).setLevel(self._logging_level)

    def run(self):
        logging.debug("***background active")
        self._initLogging()
        self._setup_audio_generator()
        self.trainSilence()
        logging.debug("process %s (%d)" % (self.name, os.getpid()))
        try:
            self._capturer = threading.Thread(target=self.captureSound)
            self._recognizer = threading.Thread(target=self.recognizeSpeech)
            self._audio = pyaudio.PyAudio()
            logging.debug("recognizer process active")
            self._recognizer.start()
            self._capturer.start()
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
        silence_sample_count = 0
        while True:
            content, seq, chunk_count, start_offset, end_offset = next(self._audio_generator)
            try:
                volume = max(array.array('h', content))
                logging.debug("sample {}".format(volume))
                if volume < 0:
                    continue
                self._silence_threshold += volume
                silence_min = min(volume, silence_min)
                silence_sample_count += 1
                if silence_sample_count > SILENCE_TRAINING_SAMPLES:
                    break
            except Exception:
                logging.exception("Training mic read raised exception")
        self._silence_threshold /= silence_sample_count
        self._silence_threshold -= abs(self._silence_threshold - silence_min)/2
        logging.info("Trained silence volume {} min was {} pause samples {}".format(self._silence_threshold, silence_min, PAUSE_LENGTH_IN_SAMPLES))

    def captureSound(self):
        logging.debug("starting capturing")
        consecutive_silent_samples = 999
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
            except IOError:
                logging.exception("IOError capturing audio")
        logging.debug("ending sound capture")
        # stop Recording
        mic_stream.stop_stream()
        mic_stream.close()
        self._audio.terminate()
        logging.debug("stopped capturing")

    def _setup_audio_generator(self):
        logging.debug("Setting up audio generator")
        mic =  microphonestream.MicrophoneStream()
        while mic.get_start_time() is None:
            time.sleep(microphonestream.CHUNK_DURATION_SECS)
        self._audio_generator = mic.generator()

    def recognizeSpeech(self):
        logging.debug("started recognizing")
        self._speech_client = speech.SpeechClient()

        language_code = 'en-US'  # a BCP-47 language tag
        speech_client = speech.SpeechClient()
        requests = (speech.StreamingRecognizeRequest(audio_content=chunk) for chunk in self._audio_stream)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=language_code)
        self._streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True)

        logging.debug("Starting recognizing")
        waiting = False
        consecutive_error_count = 0 
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
                logging.debug("recognizing speech")

                responses = client.streaming_recognize(
                    config=streaming_config, requests=requests)

                if not responses:
                    continue
                response = responses[0]
                result = response.results[0]
                if not result.alternatives:
                    continue
                alternatives = result.alternatives
                consecutive_error_count = 0 
                for alternative in alternatives:
                    logging.debug("speech: {}".format(alternative.transcript))
                    logging.debug("final: {}".format(alternative.is_final))
                    logging.debug("confidence: {}".format(alternative.confidence))
                    logging.debug("putting phrase {}".format(alternative.transcript))
                    if alternative.is_final or self._stop_recognizing:
                        self._transcript.send(alternative.transcript)
                    if self._stop_recognizing:
                        break
            except Exception:
                consecutive_error_count += 1
                logging.exception("error[%d] recognizing speech", consecutive_error_count)
                if consecutive_error_count < MAX_CONSECUTIVE_SPEECH_ERRORS:
                    continue
                logging.error('max consecutive errors reached. aborting.')
        logging.debug("stopped recognizing")

def main(argv):
    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = multiprocessingloghandler.ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_DEBUG)

    transcript = multiprocessing.Pipe()
    recognition_worker = SpeechRecognizer(transcript, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting speech recognition")
    recognition_worker.start()
    unused, _ = transcript
    unused.close()

    logging.shutdown()

    print("ended")
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)
