import re
import sys
import multiprocessing
import logging
_DEBUG = logging.DEBUG
import multiprocessingloghandler

import array
import traceback

import pyaudio
import datetime
import time
import queue
from datetime import datetime

# Audio recording parameters
_AUDIO_DATA_WIDTH = 2  # 16 bit audio data
AUDIO_RATE_HZ = 16000
CHUNK_DURATION_SECS = 0.10  # 100 ms chunks
CHUNK_SIZE = int(AUDIO_RATE_HZ * CHUNK_DURATION_SECS)

VOLUME_SILENCE_RANGE = 1.11  # Consider anything within 10% above the minimum sound to be background noise

VOLUME_INCREASE_THRESHOLD_PERCENT = abs(VOLUME_SILENCE_RANGE - 1.0)
CAPTION_DURATION_SECS = 60.0

STATE_SAMPLE_LIFETIME_SECS = 5
PAUSE_MINIMUM_SPAN_SECS = 2

class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate=AUDIO_RATE_HZ, chunk_size_bytes=CHUNK_SIZE):
        self.rate = rate
        self._chunk_size_bytes = chunk_size_bytes

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

        self._audio_base_time = None
        self._begin()

    def get_start_time(self):
        return self._audio_base_time

    def _begin(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self.rate,
            input=True, frames_per_buffer=self._chunk_size_bytes,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def _set_base_time(self):
        if self._audio_base_time is None:
            self._audio_base_time = time.time() - CHUNK_DURATION_SECS

    def close(self):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._set_base_time()
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        frame_nbr = 0
        start_time = None
        end_time = None
        chunk_count = 0
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            received_at = time.time()
            if end_time and received_at < end_time:
                logging.error('derived chunk start time < previous chunk end time')
            chunk_count += 1
            # Derive the start time from the first chunk of a buffered set 
            if not start_time:
                start_time = received_at - CHUNK_DURATION_SECS

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    received_at = time.time()
                    if chunk is None:
                        logging.warning('null audio chunk')
                        return
                    data.append(chunk)
                    chunk_count += 1
                except queue.Empty:
                    break

            frame_nbr += 1
            sound_chunk = b''.join(data)
            end_time = received_at
            soundbite = (sound_chunk, frame_nbr, chunk_count, start_time, end_time)
            logging.debug("frame %d[%d], %d, %d", frame_nbr, chunk_count, start_time, end_time)
            start_time = None
            chunk_count = 0
            yield soundbite


def main():
    mic = MicrophoneStream()
    try:
        while mic.get_start_time() is None:
            time.sleep(CHUNK_DURATION_SECS)
        audio_generator = mic.generator()
        while True:
            content, seq, chunk_count, start_offset, end_offset = next(audio_generator)
            volume = max(array.array('h', content))
            print('volume %d' % volume)
    finally:
        print('closing mic')
        mic.close()

if __name__ == '__main__':
    main()
