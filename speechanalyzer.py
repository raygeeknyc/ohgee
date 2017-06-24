import logging
import multiprocessing
from multiprocessingloghandler import ChildMultiProcessingLogHandler

from google.cloud import language

class SpeechAnalyzer(multiprocessing.Process):
    def __init__(self, transcript, log_queue, logging_level):
        multiprocessing.Process.__init__(self)
        self._transcript, _ = transcript

    def _initLogging(self):
        handler = ChildMultiProcessingLogHandler(self._log_queue)
        logging.getLogger(str(os.getpid())).addHandler(handler)
        logging.getLogger(str(os.getpid())).setLevel(self._logging_level)

    def run(self):
        self._initLogging()
        try:
            language_client = language.Client()
            self._analyzeSpeech()
        except Exception, e:
            logging.exception("***background exception: {}".format(str(e)))
        finally:
            logging.debug("***speech analyzer terminating")
  
    def _analyzeSpeech(self):
        while True:
            text = self._transcript.get()
            document = language_client.document_from_text(text)

            sentiment = document.analyze_sentiment().sentiment
            entities = document.analyze_entities().entities
            tokens = document.analyze_syntax().tokens

            print("Text: {}".format(text))
            if sentiment.score < 0:
                mood = "sad"
            elif sentiment.score > 0:
                mood = "glad"
            else:
                mood = "meh"

            print("Sentiment: {}: {}, {}".format(mood, sentiment.score, sentiment.magnitude))
            for entity in entities:
                print("Entity: {}: {}".format(entity.entity_type, entity.name))
                print("source: {}: {}".format(entity.metadata, entity.salience))

            for token in tokens:
                print("Token: {}: {}".format(token.part_of_speech, token.text_content))
