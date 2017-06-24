import os
import logging
import multiprocessing
from multiprocessingloghandler import ChildMultiProcessingLogHandler

from google.cloud import language

class SpeechAnalyzer(multiprocessing.Process):
    def __init__(self, transcript, log_queue, logging_level):
        multiprocessing.Process.__init__(self)
        _, self._transcript = transcript
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
  
    def _analyzeSpeech(self):
        logging.debug("***speech analyzer analyzing")
        while not self._exit.is_set():
            text = self._transcript.recv()
            document = self._language_client.document_from_text(text)
            print("analyzer received text: {}".format(text))

            sentiment = document.analyze_sentiment().sentiment
            entities = document.analyze_entities().entities
            tokens = document.analyze_syntax().tokens

            if sentiment.score < 0:
                mood = "sad"
            elif sentiment.score > 0:
                mood = "glad"
            else:
                mood = "meh"

            logging.info("Sentiment: {}: {}, {}".format(mood, sentiment.score, sentiment.magnitude))
            for entity in entities:
                logging.info("Entity: {}: {}".format(entity.entity_type, entity.name))
                logging.info("source: {}: {}".format(entity.metadata, entity.salience))

            for token in tokens:
                logging.info("Token: {}: {}".format(token.part_of_speech, token.text_content))
