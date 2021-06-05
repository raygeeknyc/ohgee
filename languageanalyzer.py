#!/usr/bin/python3

import os
import sys
import logging
_LOGGING_LEVEL = logging.DEBUG

import multiprocessing
from multiprocessingloghandler import ParentMultiProcessingLogHandler, ChildMultiProcessingLogHandler

from google.cloud import language_v1


MOOD_THRESHOLD = 0.2
LOWER_MOOD_THRESHOLD = -1 * MOOD_THRESHOLD

POS_NOUN = "NOUN"
POS_ADJECTIVE = "ADJ"

DEMO_PHRASES = ["Hello there Raymond", "What a cute robot", "I love to eat lettuce",
    "I hate you", "You are very adorable"]

def isGood(sentiment):
    return sentiment['score'] >= MOOD_THRESHOLD

def isBad(sentiment):
    return sentiment['score'] <= LOWER_MOOD_THRESHOLD

def isMeh(sentiment):
    return MOOD_THRESHOLD >= sentiment['score'] >= LOWER_MOOD_THRESHOLD

class LanguageAnalyzer(multiprocessing.Process):
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
            self._language_client = language_v1.LanguageServiceClient()
            self._analyzeSpeech()
            logging.debug("speech analyzer done analyzing")
        except Exception:
            logging.exception("speech analyzer exception")
        finally:
            logging.debug("speech analyzer terminating")
  
    def _analyzeSpeech(self):
        logging.debug("***speech analyzer analyzing")
        while not self._exit.is_set():
            try:
                logging.debug("waiting for text")
                text = self._text_transcript.recv()
                logging.debug("analyzing '%s'" % text)
                document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)

                content = document.content
                logging.debug("analyzer received text: {}".format(content))
                sentiment = self._language_client.analyze_sentiment(document=document).document_sentiment

                logging.debug("Sentiment: {}, {}".format(sentiment.score, sentiment.magnitude))

                response = self._language_client.analyze_entities(document=document)

                entities = response.entities
                for entity in entities:
                    logging.debug("Entity {} Type {}".format(entity.name, entity.type_.name))

                    logging.debug(u"Salience score: {}".format(entity.salience))
                    for metadata_name, metadata_value in entity.metadata.items():
                        print(u"{}: {}".format(metadata_name, metadata_value))

                response = self._language_client.analyze_syntax(document=document)

                tokens = response.tokens
                for token in tokens:
                    logging.debug("Token: {}: {}".format(token.part_of_speech.tag.name, token.text))
                noun = None
                adjective = None
                decorated_noun = None
                for token in reversed(tokens):
                    if token.part_of_speech.tag.name == POS_NOUN:
                        noun = token.text.content
                        continue
                    if token.part_of_speech.tag.name == POS_ADJECTIVE and noun:
                        adjective = token.text.content
                        break
                if noun and adjective:
                    decorated_noun = (adjective, noun)
                    logging.debug("ADJ+NOUN {}".format(decorated_noun))

                portable_tokens = [{'text':token.text.content, 'part_of_speech':token.part_of_speech.tag.name} for token in tokens]
                portable_entities = [{'name':str(entity.name), 'entity_type':str(entity.type_.name), 'salience':entity.salience} for entity in entities]
                portable_sentiment = {'score':sentiment.score, 'magnitude':sentiment.magnitude}
                results = (content, portable_tokens, portable_entities, portable_sentiment, decorated_noun)
                logging.debug("sending {}, {}, {}, {}, {}".format(type(content), type(portable_tokens), type(portable_entities), type(portable_sentiment), type(decorated_noun)))
                self._nl_results.send(results)
            except EOFError:
                logging.debug("EOF on speech analyzer input")
                break
            except Exception:
                logging.exception("Error analyzing speech")
        logging.debug("end of speech analyzer")
        self._text_transcript.close()
        self._nl_results.close()


def main(unused):
    log_stream = sys.stderr
    log_queue = multiprocessing.Queue(100)
    handler = ParentMultiProcessingLogHandler(logging.StreamHandler(log_stream), log_queue)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(_LOGGING_LEVEL)

    transcript = multiprocessing.Pipe()
    nl_results = multiprocessing.Pipe()
    language_worker = LanguageAnalyzer(transcript, nl_results, log_queue, logging.getLogger('').getEffectiveLevel())
    logging.debug("Starting language analyzer")
    language_worker.start()

    phrase_pipe, unused = transcript
    unused.close()

    unused, language_results = nl_results
    unused.close()

    for phrase in DEMO_PHRASES:
        print("sending phrase '%s'" % phrase)
        phrase_pipe.send(phrase)
    print("sent %d phrases" % len(DEMO_PHRASES))
    phrase_pipe.close()

    while True:
        try:
            phrase = language_results.recv()
            print("got %s" % str(phrase))
        except EOFError:
            print("End of NL results queue")
            break
    print("done")


if __name__ == '__main__':
    print('Running standalone language analyzer.')
    main(sys.argv)
    print('exiting')
