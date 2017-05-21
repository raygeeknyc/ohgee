import Queue
from array import array
import threading
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
    
    def processSoundBites(soundBites,transcript):
        shutdown = False
        while not shutdown:
            bite_count = 0
            content = ''
            # Block until there's a soundbite in the queue
            utterance = soundBites.get(True)
            print "Processing sound"
            if utterance == END_MESSAGE:
                print "stopping sound processor"
                shutdown = True
            else:
                for chunk in utterance.queue:
                    content += chunk.tostring()
                bite_count += 1
            # Append any additional soundbites in the queue
            while not soundBites.empty():
                utterance = soundBites.get(False)
                if utterance == END_MESSAGE:
                    print "stopping sound processor"
                    shutdown = True
                else:
                    for chunk in utterance.queue:
                        content += chunk.tostring()
                    bite_count += 1
            if bite_count:
                print "Sampling content from %d soundbites" % bite_count
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
                    print "no results"
                else:
                    print "Found %d transcripts:" % len(alternatives)
                    for alternative in alternatives:
                        print('Transcript: {}'.format(alternative.transcript))
                        print('Confidence: {}'.format(alternative.confidence))
                        transcript.put(alternative.transcript)

    def getSpeech():
        print "opening audio"
        # Start Recording
        stream = self._audio.open(format=FORMAT, channels=CHANNELS,
            rate=RATE, input=True,
            frames_per_buffer=FRAMES_PER_BUFFER)

        print "capturing"
        frames=Queue.Queue()
        transcript = Queue.Queue()
        soundprocessor = threading.Thread(target=processSoundBites, args=(frames,transcript,))
        soundprocessor.start()
        while not self._stop:
            soundbite = Queue.Queue()
            consecutive_silent_samples = 0
            volume = 0
            while volume <= SILENCE_THRESHOLD:
                data = array('h', stream.read(FRAMES_PER_BUFFER))
                volume = max(data)
            print "soundbite started"
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
                    print "pause detected"
                    break
            print "finished recording %d frames" % len(soundbite.queue)
            frames.put(soundbite)
        print "ending"
        if soundbite:
            frames.put(soundbite)
        # stop Recording
        stream.stop_stream()
        stream.close()
        self._audio.terminate()
        print "Waiting for processor to exit"
        frames.put(END_MESSAGE)
        soundprocessor.join()
        print("Transcript %s" % " ".join(transcript.queue))
