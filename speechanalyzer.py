import os
from random import randint
import logging
import multiprocessing
from multiprocessingloghandler import ChildMultiProcessingLogHandler

from google.cloud import language

MOOD_THRESHOLD = 0.2
LOWER_MOOD_THRESHOLD = -1 * MOOD_THRESHOLD

GREETINGS = (["hello"],["hi"],["good", "morning"], ["hey", "there"])
FAREWELLS = (["goodnight"], ["goodbye"], ["bye"], ["farewell"], ["good", "night"], ["see","you"])
AFFECTIONS = (["I", "love", "you"], ["I", "like", "you"], ["you're", "the", "best"])
ME_TOO = (["I", "feel", "the", "same"], ["that", "makes", "two", "of", "us"], ["I", "feel", "the", "same", "way"], ["same", "here"])
THANKS = (["thank", "you"], ["thanks"])
WELCOMES = (["you're", "welcome"], ["don't", "mention", "it"], ["de", "nada"], ["my", "pleasure"])
HATES = (["I", "hate", "you"], ["I", "don't", "like", "you"], ["you", "suck"])
SADNESSES = (["sniff"], ["you", "break", "my", "heart"], ["that", "makes", "me", "sad"], ["I'm", "sorry"])
IN_KIND_SUFFIXES=(["to","you"], ["as","well"], ["too"], ["also"], ["to","you","as","well"], [], [], [])

PROMPTS_RESPONSES = [(GREETINGS, GREETINGS, IN_KIND_SUFFIXES, True), 
  (FAREWELLS, FAREWELLS, IN_KIND_SUFFIXES, True),
  (AFFECTIONS, ME_TOO + AFFECTIONS, IN_KIND_SUFFIXES, False),
  (THANKS, WELCOMES, None, False),
  (HATES, SADNESSES, None, False)]

def randomPhraseFrom(phrases):
    if not phrases: return []
    return phrases[randint(0,len(phrases)-1)]

def getResponse(tokens):
    for prompts, responses, suffixes, wave_flag in PROMPTS_RESPONSES:
        if phraseMatch(tokens, prompts):
            return (randomPhraseFrom(responses)+randomPhraseFrom(IN_KIND_SUFFIXES), wave_flag)
    return None

def phraseMatch(tokens, phrases):
    for phrase in phrases:
        matchedTokens = phraseInTokens(tokens, phrase)
        if matchedTokens:
            return matchedTokens
    return []

def phraseInTokens(tokens, phrase):
    if not phrase or not tokens:
        return []
    w = phrase[0]
    matched = True
    for i in range(len(tokens)-len(phrase)+1):
        if tokens[i].text_content.upper() == w.upper():
            for j in range(1,len(phrase)):
                if tokens[i+j].text_content.upper() != phrase[j].upper():
                    matched = False
            if matched:
                return tokens[i:i+len(phrase)]
    return []

def greeted(tokens):
    return phraseMatch(tokens, GREETINGS)

def departed(tokens):
    return phraseMatch(tokens, FAREWELLS)

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
            logging.debug("analyzer received text: {}".format(text))

            sentiment = document.analyze_sentiment().sentiment

            logging.debug("Sentiment: {}, {}".format(sentiment.score, sentiment.magnitude))
            for entity in entities:
                logging.debug("Entity: {}: {}".format(entity.entity_type, entity.name))
                logging.debug("source: {}: {}".format(entity.metadata, entity.salience))

            for token in tokens:
                logging.debug("Token: {}: {}".format(token.part_of_speech, token.text_content))
            results = (tokens, entities, sentiment)
            self._nl_results.send(results)
