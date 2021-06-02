import re
import sys
import logging
_DEBUG = logging.INFO
from google.cloud import speech
import microphonestream

import array
import traceback
import threading
import queue
from queue import Queue
from queue import Empty

import datetime
import time
from datetime import datetime

SILENCE_TRAINING_SAMPLES = 10
FRAMES_PER_BUFFER = 4096


class AudioProcessor(object):
    def __init__(self, rate=microphonestream.AUDIO_RATE_HZ):
        logging.getLogger('').setLevel(_DEBUG)
        self._stop_analyzing = False
        self._response_start_time = None
        self.rate = rate
        self._setup_speech()

    def trainSilence(self, audio_generator):
        logging.debug("Training silence")
        self._silence_threshold = 0
        silence_min = 9999
        silence_sample_count = 0
        while True:
            content, seq, chunk_count, start_offset, end_offset = next(audio_generator)
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

    def _setup_speech(self):
        language_code = 'en-US'  # a BCP-47 language tag
        self._speech_client = speech.SpeechClient()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.rate,
            language_code=language_code,
            enable_word_time_offsets=True)
        self._streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=False)

    def extract_sound_metadata(self, sound_chunk, seq, start, end):
      if self._response_start_time is None:
        self._response_start_time = start
      requests = speech.StreamingRecognizeRequest(audio_content=sound_chunk)
      return requests

    def process_microphone_stream(self):
        mic = microphonestream.MicrophoneStream()
        while mic.get_start_time() is None:
            time.sleep(microphonestream.CHUNK_DURATION_SECS)
        audio_generator = mic.generator()
        self.trainSilence(audio_generator)
        while True:
            requests = (self.extract_sound_metadata(content, seq, start_offset, end_offset)
                 for content, seq, chunk_count, start_offset, end_offset in audio_generator)
            logging.info('created requests generator')
            responses = self._speech_client.streaming_recognize(self._streaming_config, requests)
            try:
                self.render_speech_responses(responses, mic.get_start_time())
            except:
                traceback.print_exc()
            finally:
                break

    def render_speech_responses(self, responses, audio_start_time):
        """Iterates through server responses and prints them.

        The responses passed is a generator that will block until a response
        is provided by the server.

        Each response may contain multiple results, and each result may contain
        multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
        print only the transcription for the top alternative of the top result.

        If a caption file is specified, print final responses to a caption file
        with timestamps every minute.
        """
        logging.info('audio start %f', audio_start_time)
        last_phrase = ''
        last_caption_timestamp = 0
        for response in responses:
            logging.debug('response from %f, %s', self._response_start_time, response)
            self._response_start_time = None
            if not response.results:
                continue

            # The `results` list is consecutive. For streaming, we only care about
            # the first result being considered, since once it's `is_final`, it
            # moves on to considering the next utterance.
            result = response.results[0]

            if not result.alternatives:
                continue
            logging.debug("result: {}".format(result)) 
    
            # Display the transcription of the top alternative.
            words = result.alternatives[0].words

            if words:
                phrase = " ".join([word.word for word in words])
                print(phrase)

                # Exit recognition if our exit word is said 3 times
                if result.is_final and len(re.findall(r'quit', phrase, re.I)) == 3:
                    print('Exiting..')
                    break


def main(argv):
    sound_processor = AudioProcessor()
    sound_processor.process_microphone_stream()

    logging.info("logged: main done")
    logging.shutdown()

    print("ended")
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)
