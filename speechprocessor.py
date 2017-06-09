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
from google.cloud import speech

# Setup audio and cloud speech
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
FRAMES_PER_BUFFER = 8192
SILENCE_THRESHOLD = 700
PAUSE_LENGTH_SECS = 1
MAX_BUFFERED_SAMPLES = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)

def log(message):
    pass

class SpeechProcessor(multiprocessing.Process):
    def __init__(self, transcript):
        multiprocessing.Process.__init__(self)
        i, o = transcript
        self._exit = multiprocessing.Event()
        self._transcript = i
        self._speech_client = speech.Client()
        self._ingester = threading.Thread(target=self.getSound)
        self._processor = threading.Thread(target=self.processSound)
        self._stop_capturing = False
        self._stop_recognizing = False
        self._audio = pyaudio.PyAudio()
        self._transcript = transcript
        self._audio_stream = StreamRW(io.BytesIO(), MAX_BUFFERED_SAMPLES*FRAMES_PER_BUFFER*2)

    def stop(self):
        log("***background received shutdown")
        self._exit.set()

    def run(self):
        try:
            log("***background active")
            self._processor.start()
            self._ingester.start()
            self._exit.wait()
 
        except Exception, e:
            log("***background exception: {}".format(e))
        log("***background terminating")
        self._stopCapturing()
        self._stopProcessing()
        self._ingester.join()
        self._processor.join()

    def _stopCapturing(self):
        self._stop_capturing = True
    
    def _stopProcessing(self):
        self._stop_recognizing = True

    def getSound(self):
        log("capturing")
        mic_stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        consecutive_silent_samples = 0
        samples = 0
 
        while not self._stop_capturing:
            samples += 1
            volume = 0
            try:
                data = array.array('h', mic_stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
                if volume <= SILENCE_THRESHOLD:
                    consecutive_silent_samples += 1
                else:
                    consecutive_silent_samples = 0
                l=self._audio_stream.write(data)
                log("wrote {} bytes".format(l))
                log("Vol: {}".format(volume))
                if not samples % MAX_BUFFERED_SAMPLES or consecutive_silent_samples >= PAUSE_LENGTH_IN_SAMPLES or self._stop_capturing:
                    self._audio_stream.flush()
                    log("flush")
            except IOError:
                log("-")
 
        log("ending sound capture")
        # stop Recording
        mic_stream.stop_stream()
        mic_stream.close()
        self._audio.terminate()
        log("stopped producing")

    def processSound(self):
        log("processing sound")
        audio_sample = self._speech_client.sample(
            stream=self._audio_stream,
            source_uri=None,
            encoding=speech.encoding.Encoding.LINEAR16,
            sample_rate_hertz=RATE)
        o, i = self._transcript
        while not self._stop_recognizing:
            try:
                alternatives = audio_sample.streaming_recognize('en-US',
                    interim_results=True)
                for alternative in alternatives:
                    log("speech: {}".format(alternative.transcript))
                    if alternative.is_final:
                        o.send(alternative.transcript)
            except Exception, e:
                alternatives = None
                log("error processing speech: {}".format(e))
        o.close()
        log("stopped processing")
