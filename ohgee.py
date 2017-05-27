import logging
_DEBUG = logging.INFO

import Queue
from array import array
import threading
import time
import io
import sys
import pyaudio
from streamrw import StreamRW
 
# Import the Google Cloud client libraries
from google.cloud import speech
from google.cloud import language

# First you have to authenticate for the default application: gcloud auth application-default login

# Setup audio and cloud speech
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
FRAMES_PER_BUFFER = 4096
SILENCE_THRESHOLD = 700
PAUSE_LENGTH_SECS = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)
 
class SpeechProcessor():
    def __init__(self, transcript):
        self._stop_recording = False
        self._stop_recognizing = False
        self._speech_client = speech.Client()
        self._audio = pyaudio.PyAudio()
        self._transcript = transcript
        self._audio_stream = StreamRW(io.BytesIO(), RATE*FRAMES_PER_BUFFER)
        self.speech_recognizer = threading.Thread(target=self.processSoundBites )
        self.speech_recognizer.start()

    def stop_recognizing(self):
        self._stop_recognizing = True
    
    def stop_recording(self):
        self._stop_recording = True
    
    def processSoundBites(self):
        audio_sample = self._speech_client.sample(
            stream=self._audio_stream,
            source_uri=None,
            encoding=speech.encoding.Encoding.LINEAR16,
            sample_rate_hertz=RATE)

        # Find transcriptions of the audio content
        try:
            logging.info("Processing sound")
            while True:
                alternatives = audio_sample.streaming_recognize('en-US',
                    interim_results=True)
                for alternative in alternatives:
                    logging.info('Transcript: {}'.format(alternative.transcript))
                    logging.debug('Finished: {}'.format(alternative.is_final))
                    logging.debug('Stability: {}'.format(alternative.stability))
                    logging.debug('Confidence: {}'.format(alternative.confidence))
                    if alternative.is_final:
                        self._transcript.put(alternative.transcript)
                if self._stop_recognizing: break
        except:
            alternatives = None
            logging.error("could not set up recognizer")
        logging.debug("stopped recognizing")

    def getSound(self):
        # Start Recording
        mic_stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        consecutive_silent_samples = 0
        logging.info("capturing")
        samples = 0
        while True:
            samples += 1
            volume = 0
            try:
                data = array('h', mic_stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
                logging.debug("volume: {}".format(volume))
                if volume <= SILENCE_THRESHOLD:
                    consecutive_silent_samples += 1
                else:
                    consecutive_silent_samples = 0
                self._audio_stream.write(data)
                if not samples % 10:
                    self._audio_stream.flush()
                if consecutive_silent_samples >= PAUSE_LENGTH_IN_SAMPLES:
                    logging.debug("pause detected")
            except IOError:
                logging.debug("-")
            if self._stop_recording:
                self.stop_recognizing()
                break
        logging.info("ending")
        # stop Recording
        mic_stream.stop_stream()
        mic_stream.close()
        self._audio.terminate()

    def waitForFinalTranscript(self):
        logging.debug("Waiting for processor to exit")
        self.speech_recognizer.join()

if __name__ == '__main__':
    logging.getLogger().setLevel(_DEBUG)
    logging.info("Starting speech analysis")
    transcript = Queue.Queue()
    speech_processor = SpeechProcessor(transcript)
    try:
        speech_processor.getSound()
    #    sound_ingester = threading.Thread(target=speech_processor.getSound)
    #    sound_ingester.start()
    #    while True:
    #        time.sleep(10)
    except KeyboardInterrupt:
        logging.info("Stopping speech analysis")
        speech_processor.stop_recording()
        speech_processor.stop_recognizing()
        speech_processor.waitForFinalTranscript()
        logging.info("Final transcript: '%s'" % ";".join(transcript.queue))
        sys.exit()
