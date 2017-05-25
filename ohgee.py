import Queue
from array import array
import threading
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
FRAMES_PER_BUFFER = 2048
MAX_SOUNDBITE_SECS = 10
SILENCE_THRESHOLD = 500
END_MESSAGE = "Abort!Abort!Abort!"
PAUSE_LENGTH_SECS = 1
PAUSE_LENGTH_IN_SAMPLES = int((PAUSE_LENGTH_SECS * RATE / FRAMES_PER_BUFFER) + 0.5)
 
class SpeechProcessor():
    def __init__(self):
        self._stop = False
        signal.signal(signal.SIGINT, _sigint_handler)
        self._speech_client = speech.Client()
        self._audio = pyaudio.PyAudio()

    def _sigint_handler():
        self._stop = True
    
    def processSoundBites(audio_stream, transcript):
        shutdown = False
        audio_sample = self._speech_client.sample(
            stream=audio_stream,
            source_uri=None,
            encoding=speech.encoding.Encoding.LINEAR16,
            sample_rate_hertz=RATE)

        while not shutdown:
            print "Processing sound"
            # Find transcriptions of the audio content
            try:
                alternatives = audio_sample.streaming_recognize('en-US')
            except:
                alternatives = None
            for alternative in alternatives:
                print('Finished: {}'.format(alternative.is_final))
                print('Stability: {}'.format(alternative.stability))
                print('Confidence: {}'.format(alternative.confidence))
                print('Transcript: {}'.format(alternative.transcript))
                if alternative.is_final:
                    transcript.put(alternative.transcript)

    def getSpeech():
        print "opening audio"
        # Start Recording
        stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        print "capturing"
        transcript = Queue.Queue()
        audio_pipe = StreamRW(io.BytesIO())
        soundprocessor = threading.Thread(target=processSoundBites, args=(audio_pipe, transcript,))
        soundprocessor.start()
        while not self._stop:
            soundbite = Queue.Queue()
            consecutive_silent_samples = 0
            volume = 0
            while volume <= SILENCE_THRESHOLD:
                data = array('h', stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
            print "sound started"
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
                    print "pause detected"
        print "ending"
        # stop Recording
        stream.stop_stream()
        stream.close()
        self._audio.terminate()
        print "Waiting for processor to exit"
        soundprocessor.join()
        print("Transcript %s" % " ".join(transcript.queue))
