import logging
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
RATE = 16000
FRAMES_PER_BUFFER = 1024
MAX_SOUNDBITE_SECS = 10
SILENCE_THRESHOLD = 500
END_MESSAGE = "Abort!Abort!Abort!"
PAUSE_LENGTH_SECS = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)
 
class SpeechProcessor():
    def __init__(self):
        self._stop = False
        self._speech_client = speech.Client()
        self._audio = pyaudio.PyAudio()

    def stop(self):
        self._stop = True
    
    def processSoundBites(self, audio_stream, transcript):
        audio_sample = self._speech_client.sample(
            stream=audio_stream,
            source_uri=None,
            encoding=speech.encoding.Encoding.LINEAR16,
            sample_rate_hertz=RATE)

        while not self._stop:
            logging.info("Processing sound")
            # Find transcriptions of the audio content
            try:
                alternatives = audio_sample.streaming_recognize('en-US')
            except:
                alternatives = None
            for alternative in alternatives:
                logging.debug('Finished: {}'.format(alternative.is_final))
                logging.debug('Stability: {}'.format(alternative.stability))
                logging.debug('Confidence: {}'.format(alternative.confidence))
                logging.debug('Transcript: {}'.format(alternative.transcript))
                if alternative.is_final:
                    transcript.put(alternative.transcript)

    def getSpeech(self):
        # Start Recording
        stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        logging.info("capturing")
        transcript = Queue.Queue()
        audio_pipe = StreamRW(io.BytesIO())
        soundprocessor = threading.Thread(target=self.processSoundBites, args=(audio_pipe, transcript,))
        soundprocessor.start()
        while not self._stop:
            soundbite = Queue.Queue()
            consecutive_silent_samples = 0
            volume = 0
            while volume <= SILENCE_THRESHOLD:
                data = array('h', stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
            logging.debug("sound started")
            audio_pipe.write(data)
            remaining_samples = int((MAX_SOUNDBITE_SECS * RATE / FRAMES_PER_BUFFER) + 0.5) - 1
            for i in range(0, remaining_samples):
                data = array('h', stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
                if volume <= SILENCE_THRESHOLD:
                    consecutive_silent_samples += 1
                else:
                    consecutive_silent_samples = 0
                audio_pipe.write(data)
                if consecutive_silent_samples >= PAUSE_LENGTH_IN_SAMPLES:
                    logging.debug("pause detected")
        logging.info("ending")
        # stop Recording
        stream.stop_stream()
        stream.close()
        self._audio.terminate()
        logging.debug("Waiting for processor to exit")
        soundprocessor.join()
        logging.info("Final transcript %s" % " ".join(transcript.queue))

logging.getLogger().setLevel(logging.INFO)
logging.info("Starting speech analysis")
speech_processor = SpeechProcessor()
try:
    sound_ingester = threading.Thread(target=speech_processor.getSpeech)
    sound_ingester.start()
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    logging.info("Stopping speech analysis")
    speech_processor.stop()
    sound_ingester.join()
    sys.exit()
