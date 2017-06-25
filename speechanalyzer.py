import os
import logging
import multiprocessing
from multiprocessingloghandler import ChildMultiProcessingLogHandler

from google.cloud import language

MOOD_THRESHOLD = 0.1
LOWER_MOOD_THRESHOLD = -1 * MOOD_THRESHOLD

class SpeechAnalyzer(multiprocessing.Process):
    def __init__(self, text_transcript, nl_results, log_queue, logging_level):
        multiprocessing.Process.__init__(self)
        _, self._text_transcript = text_transcript
        self._nl_results, _ = nl_results
        self._exit = multiprocessing.Event()
        self._log_queue = log_queue
        self._logging_level = logging_level

    def _initLogging(self):
        handler = ChildMultiProcessingLogHandler(self._log_queue)
        logging.getLogger(str(os.getpid())).addHandler(handler)
        logging.getLogger(str(os.getpid())).setLevel(self._logging_level)

    def stop(self):
        logging.debug("speech analyzer received shutdown")
        self._exit.set()

    def run(self):
        self._initLogging()
        logging.debug("***speech analyzer starting")
        try:
            self._language_client = language.Client()
            self._analyzeSpeech()
            logging.debug("speech analyzer done analyzing")
        except Exception, e:
            logging.exception("speech analyzer exception: {}".format(str(e)))
        finally:
            logging.debug("speech analyzer terminating")
            self._nl_results.close()
  
    def _analyzeSpeech(self):
        logging.debug("***speech analyzer analyzing")
        while not self._exit.is_set():
            text = self._text_transcript.recv()
            document = self._language_client.document_from_text(text)
            entities = document.analyze_entities().entities
            tokens = document.analyze_syntax().tokens
            print("analyzer received text: {}".format(text))

            sentiment = document.analyze_sentiment().sentiment
            if sentiment.score < LOWER_MOOD_THRESHOLD:
                mood = "sad"
            elif sentiment.score > MOOD_THRESHOLD:
                mood = "glad"
            else:
                mood = "meh"

            logging.debug("Sentiment: {}: {}, {}".format(mood, sentiment.score, sentiment.magnitude))
            for entity in entities:
                logging.debug("Entity: {}: {}".format(entity.entity_type, entity.name))
                logging.debug("source: {}: {}".format(entity.metadata, entity.salience))

            for token in tokens:
                logging.debug("Token: {}: {}".format(token.part_of_speech, token.text_content))
            results = (tokens, entities, sentiment)
            self._nl_results.send(results)
