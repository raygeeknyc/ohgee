import os
from random import randint
import logging
import multiprocessing
from multiprocessingloghandler import ChildMultiProcessingLogHandler

from google.cloud import language

MOOD_THRESHOLD = 0.2
LOWER_MOOD_THRESHOLD = -1 * MOOD_THRESHOLD

GREETINGS = (["hello"],["hi"],["good", "morning"], ["hey", "there"], ["good", "day"], ["nice", "to", "see", "you"], ["good", "to", "see", "you"], ["welcome"])
FAREWELLS = (["goodnight"], ["goodbye"], ["bye"], ["farewell"], ["good", "night"], ["see","you"], ["talk", "to", "you", "later"], ["take", "care"], ["bye", "bye"], ["see", "you", "later"])
AFFECTIONS = (["you're", "adorable"], ["I", "adore", "you"], ["I", "love", "you"], ["I", "like", "you"], ["you're", "the", "best"], ["you're", "cute"], ["you're", "so", "cute"], ["you're", "sweet"], ["you're", "so", "sweet"], ["you're", "cool"], ["you're", "great"], ["cute", "robot"], ["you're", "awesome"], ["you're", "amazing"])
ME_TOO = (["I", "feel", "the", "same"], ["that", "makes", "two", "of", "us"], ["I", "feel", "the", "same", "way"], ["same", "here"])
THANKS = (["thank", "you"], ["thanks"])
WELCOMES = (["you're", "welcome"], ["don't", "mention", "it"], ["day", "nada"], ["my", "pleasure"], ["no", "worries"])
HATES = (["I", "hate", "you"], ["I", "don't", "like", "you"], ["you", "suck"], ["you're", "stupid"], ["you're", "awful"], ["stupid", "robot"], ["dumb", "robot"], ["you", "stink"])
SADNESSES = (["sniff"], ["you", "break", "my", "heart"], ["that", "makes", "me", "sad"], ["I'm", "sorry"], ["ouch"], ["that", "hurts"], ["I'm", "so", "sorry"])
PINGS = (["ping", "me"], ["pinging", "you"])
ACKS = (["pong"], ["ack"], ["right", "back", "at", "you"])
OTHER_PRODUCTS = (["bing", "sucks"], ["bing"])
PRODUCT_RECS = (["go", "chrome"], ["make", "mine", "chrome"], ["go", "google"])
# Add in empty lists to weigh the random selection from the tuple towards null responses
IN_KIND_SUFFIXES=(["to","you"], ["as","well"], ["too"], ["also"], ["to","you","as","well"], [], [], [], [], [], [], [])

PROMPTS_RESPONSES = [(GREETINGS, GREETINGS, IN_KIND_SUFFIXES, True), 
  (FAREWELLS, FAREWELLS, IN_KIND_SUFFIXES, True),
  (AFFECTIONS, ME_TOO + AFFECTIONS, IN_KIND_SUFFIXES, False),
  (THANKS, WELCOMES, None, False),
  (PINGS, ACKS, None, False),
  (HATES, SADNESSES, None, False),
  (OTHER_PRODUCTS, PRODUCT_RECS, None, False)]

def randomPhraseFrom(phrases):
    if not phrases: return []
    return phrases[randint(0,len(phrases)-1)]

def getResponse(phrase):
    logging.debug("Looking to match phrase {}".format(phrase))
    for prompts, responses, suffixes, wave_flag in PROMPTS_RESPONSES:
        if phraseMatch(phrase, prompts):
            return (randomPhraseFrom(responses)+randomPhraseFrom(suffixes), wave_flag)
    return None

def phraseMatch(phrase, phrases):
    for candidate_phrase in phrases:
        logging.debug("Matching with {}".format(candidate_phrase))
        matched_phrase = phraseInTokens(phrase, candidate_phrase)
        if matched_phrase:
            return matched_phrase
    return []

def phraseInTokens(phrase, candidate_phrase):
    if not phrase or not candidate_phrase:
        return []
    w = candidate_phrase[0]
    matched = True
    words = phrase.split(" ")
    for i in range(len(words)-len(candidate_phrase)+1):
        if words[i].upper() == w.upper():
            for j in range(1,len(candidate_phrase)):
                if words[i+j].upper() != candidate_phrase[j].upper():
                    matched = False
            if matched:
                return words[i:i+len(candidate_phrase)]
    return []

def getFarewell():
    return randomPhraseFrom(FAREWELLS)

def getGreeting():
    return randomPhraseFrom(GREETINGS)

def greeted(phrase):
    return phraseMatch(phrase, GREETINGS)

def departed(phrase):
    return phraseMatch(phrase, FAREWELLS)

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
                results = (content, tokens, entities, sentiment)
                self._nl_results.send(results)
            except EOFError:
                logging.debug("EOF on speech analyzer input")
                break
            except Exception, e:
                logging.exception("Error analyzing speech {}".format(e))
        logging.debug("end of speech analyzer")
        self._text_transcript.close()
        self._nl_results.close()
