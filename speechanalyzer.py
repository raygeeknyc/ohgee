import os
import logging
import multiprocessing
from multiprocessingloghandler import ChildMultiProcessingLogHandler

from google.cloud import language

MOOD_THRESHOLD = 0.2
LOWER_MOOD_THRESHOLD = -1 * MOOD_THRESHOLD

POS_NOUN = "NOUN"
POS_ADJECTIVE = "ADJ"

def isGood(sentiment):
    return sentiment.score >= MOOD_THRESHOLD

def isBad(sentiment):
    return sentiment.score <= LOWER_MOOD_THRESHOLD

def isMeh(sentiment):
    return MOOD_THRESHOLD >= sentiment.score >= LOWER_MOOD_THRESHOLD

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
            logging.exception("speech analyzer exception")
        finally:
            logging.debug("speech analyzer terminating")
  
    def _analyzeSpeech(self):
        logging.debug("***speech analyzer analyzing")
        while not self._exit.is_set():
            try:
                text = self._text_transcript.recv()
                document = self._language_client.document_from_text(text)
                content = document.content
                logging.debug("analyzer received text: {}".format(content))
                entities = document.analyze_entities().entities
                tokens = document.analyze_syntax().tokens
                sentiment = document.analyze_sentiment().sentiment

                logging.debug("Sentiment: {}, {}".format(sentiment.score, sentiment.magnitude))
                for entity in entities:
                    logging.debug("Entity: {}: {}".format(entity.entity_type, entity.name))
                    logging.debug("source: {}: {}".format(entity.metadata, entity.salience))

                for token in tokens:
                    logging.debug("Token: {}: {}".format(token.part_of_speech, token.text_content))
                noun = None
                adjective = None
                decorated_noun = None
                for token in reversed(tokens):
                    if token.part_of_speech == POS_NOUN:
                        noun = token.text_content
                        continue
                    if token.part_of_speech == POS_ADJECTIVE and noun:
                        adjective = token.text_content
                        break
                if noun and adjective:
                    decorated_noun = (adjective, noun)
                    logging.debug("ADJ+NOUN {}".format(decorated_noun))

                results = (content, tokens, entities, sentiment, decorated_noun)
                self._nl_results.send(results)
            except EOFError:
                logging.debug("EOF on speech analyzer input")
                break
            except Exception, e:
                logging.exception("Error analyzing speech")
        logging.debug("end of speech analyzer")
        self._text_transcript.close()
        self._nl_results.close()
