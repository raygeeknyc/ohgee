import logging
_DEBUG = logging.DEBUG

import multiprocessing
import threading
from streamrw import StreamRW
import pyaudio
import array
import Queue
import time
import io
import sys
import os, signal

global STOP

# Setup audio and cloud speech
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
FRAMES_PER_BUFFER = 4096
SILENCE_THRESHOLD = 700
PAUSE_LENGTH_SECS = 1
SPEECH_WAIT_SECS = 2
MAX_BUFFERED_SAMPLES = 3
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)

class Background(multiprocessing.Process):
    def __init__(self, transcript):
        multiprocessing.Process.__init__(self)
        i, o = transcript
        self._exit = multiprocessing.Event()
        self._transcript = i
        self._ingester = threading.Thread(target=self.getSound)
        self._processor = threading.Thread(target=self.processSound)
        self._stop_recording = False
        self._stop_recognizing = False
        self._speech_client = speech.Client()
        self._audio = pyaudio.PyAudio()
        self._transcript = transcript
        self._audio_stream = StreamRW(io.BytesIO(), RATE*FRAMES_PER_BUFFER)

    def stop(self):
        print("***background received shutdown")
        self._exit.set()

    def run(self):
        try:
            print("***background active")
            self._processor.start()
            self._ingester.start()
            self._exit.wait()
 
        except Exception, e:
            print("***background exception: {}".format(e))
        print("***background terminating")
        self.stop()
        self._stopCapturing()
        self._stopProcessing()
        self._ingester.join()
        self._processor.join()

    def _stopCapturing(self):
        self._stop_capturing = True
    
    def _stopProcessing(self):
        self._stop_processing = True

    def getSound(self):
        print("capturing")
        mic_stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        consecutive_silent_samples = 0
        samples = 0
 
        while not self._stop_capturing:
            samples += 1
            volume = 0
            try:
                data = array('h', mic_stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
                if volume <= SILENCE_THRESHOLD:
                    consecutive_silent_samples += 1
                else:
                    consecutive_silent_samples = 0
                self._audio_stream.write(data)
                if not samples % MAX_BUFFERED_SAMPLES or consecutive_silent_samples >= PAUSE_LENGTH_IN_SAMPLES or self._stop_capturing:
                    self._audio_stream.flush()
            except IOError:
                print("-")
 
        print("ending sound capture")
        # stop Recording
        mic_stream.stop_stream()
        mic_stream.close()
        self._audio.terminate()
        print("stopped producing")

    def processSound(self):
        print("performing")
        audio_sample = self._speech_client.sample(
            stream=self._audio_stream,
            source_uri=None,
            encoding=speech.encoding.Encoding.LINEAR16,
            sample_rate_hertz=RATE)
        while not self._stop_processing:
            try:
                alternatives = audio_sample.streaming_recognize('en-US',
                    interim_results=True)
                for alternative in alternatives:
                    if alternative.is_final:
                        self._transcript.send(alternative.transcript)
            except Exception, e:
                alternatives = None
                print("error processing speech: {}".format(e))
        print("stopped processing")

def runSpeechProcessor(background_process):
    logging.debug("starting background Speech Processor")
    background_process.run()
