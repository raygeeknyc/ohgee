import logging
import Queue
from array import array
import threading
import time
import sys
import pyaudio
 
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
        
    def processSoundBites(self,soundBites,transcript):
        shutdown = False
        while not shutdown:
            bite_count = 0
            content = ''
            # Block until there's a soundbite in the queue
            utterance = soundBites.get(True)
            logging.debug("Received  soundbite")
            if utterance == END_MESSAGE:
                logging.debug("stopping sound processor")
                shutdown = True
            else:
                for chunk in utterance.queue:
                    content += chunk.tostring()
                bite_count += 1
            # Append any additional soundbites in the queue
            while not soundBites.empty():
                utterance = soundBites.get(False)
                if utterance == END_MESSAGE:
                    logging.debug("stopping sound processor")
                    shutdown = True
                else:
                    for chunk in utterance.queue:
                        content += chunk.tostring()
                    bite_count += 1
            if bite_count:
                logging.debug("Sampling content from %d soundbites" % bite_count)
                audio_sample = self._speech_client.sample(
                    content=content,
                    source_uri=None,
                    encoding=speech.encoding.Encoding.LINEAR16,
                    sample_rate_hertz=RATE)

                # Find transcriptions of the audio content
                try:
                    alternatives = audio_sample.recognize('en-US')

                except:
                    alternatives = None
                if not alternatives:
                    logging.debug("no results")
                else:
                    for alternative in alternatives:
                        logging.info('Transcript: {}'.format(alternative.transcript))
                        logging.info('Confidence: {}'.format(alternative.confidence))
                        transcript.put(alternative.transcript)

    def getSpeech(self):
        # Start Recording
        stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        logging.info("capturing audio")
        frames=Queue.Queue()
        transcript = Queue.Queue()
        soundprocessor = threading.Thread(target=self.processSoundBites, args=(frames,transcript,))
        soundprocessor.start()
        while not self._stop:
            soundbite = Queue.Queue()
            consecutive_silent_samples = 0
            volume = 0
            while volume <= SILENCE_THRESHOLD:
                data = array('h', stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
            soundbite.put(data)
            remaining_samples = int((MAX_SOUNDBITE_SECS * RATE / FRAMES_PER_BUFFER) + 0.5) - 1
            for i in range(0, remaining_samples):
                data = array('h', stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
                if volume <= SILENCE_THRESHOLD:
                    consecutive_silent_samples += 1
                else:
                    consecutive_silent_samples = 0
                soundbite.put(data)
                if consecutive_silent_samples >= PAUSE_LENGTH_IN_SAMPLES:
                    logging.debug("pause detected")
                    break
            frames.put(soundbite)
            logging.debug("finished recording %d frames" % len(soundbite.queue))
        # stop Recording
        stream.stop_stream()
        stream.close()
        self._audio.terminate()
        logging.debug("Waiting for processor to exit")
        frames.put(END_MESSAGE)
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
