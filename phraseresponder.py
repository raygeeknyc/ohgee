# BUG - single list tuples below raise an error in getResponse()
import logging
_DEBUG=logging.INFO
_DEBUG=logging.DEBUG

import os
from random import randint
from datetime import datetime

POP_1_PROMPTS = (["who", "is", "the", "man"], ["who", "would", "risk", "his", "neck"], ["his", "neck", "for", "his", "brother", "man"], ["the", "cat", "that", "won't", "cop", "out", "when"], ["danger", "all", "about"] )
POP_1_RESPONSES = (["SHAFT"], ["that's", "shaft"], ["john", "shaft"])

POP_2_PROMPTS = (["is", "a", "bad", "mother"], ["they", "say", "this", "shaft", "is"])
POP_2_RESPONSES = (["shut", "your", "mouth"], ["shut", "your", "mouth"])

POP_3_PROMPTS = (["talking", "about", "shaft"], ["talking", "bout", "shaft"])
POP_3_RESPONSES = (["we", "can", "dig", "it"], ["dig", "it"], ["right", "on"])

POP_4_PROMPTS = (["shut", "your", "mouth"], ["shut", "your", "mouth"])
POP_4_RESPONSES = (["hey", "I'm", "talking", "about", "shaft"], ["hey", "I'm", "talkin", "bout", "shaft"])

NEWS_1_PROMPTS = (["president" ,"trump"], ["donald", "trump"])
NEWS_1_RESPONSES = (["Trump", "is", "a", "chump"], ["donald", "chump"])

BANAL_1_PROMPTS = (["you", "know", "what"], ["guess", "what"])
BANAL_1_RESPONSES = (["what?"],["no", "what?"])

BANAL_2_PROMPTS = (["how's", "the", "weather"], ["hows", "the", "weather"])
BANAL_2_RESPONSES = (["chili", "today", "hot", "tamale"], ["chili", "today", "hot", "tamale"])

GREETINGS = (["hello"],["hi"], ["hey", "there"], ["nice", "to", "see", "you"], ["good", "to", "see", "you"], ["welcome"], ["good", "day"])
ALL_DAY_GREETINGS = (["good", "morning"], ["good", "afternoon"], ["good", "evening"], ["good", "night"])
FAREWELLS = (["goodbye"], ["bye"], ["farewell"], ["see","you"], ["talk", "to", "you", "later"], ["take", "care"], ["bye", "bye"], ["see", "you", "later"])
AFFECTIONS = (["you're", "adorable"], ["I", "adore", "you"], ["I", "love", "you"], ["I", "like", "you"], ["you're", "the", "best"], ["you're", "cute"], ["you're", "so", "cute"], ["you're", "sweet"], ["you're", "so", "sweet"], ["you're", "cool"], ["you're", "great"], ["cute", "robot"], ["you're", "awesome"], ["you're", "amazing"])
ME_TOOS = (["I", "feel", "the", "same"], ["that", "makes", "two", "of", "us"], ["I", "feel", "the", "same", "way"], ["same", "here"])
THANKS = (["thank", "you"], ["thanks"])
WELCOMES = (["you're", "welcome"], ["don't", "mention", "it"], ["day", "nada"], ["my", "pleasure"], ["no", "worries"])
HATES = (["I", "hate", "you"], ["I", "don't", "like", "you"], ["you", "suck"], ["you're", "stupid"], ["you're", "awful"], ["stupid", "robot"], ["dumb", "robot"], ["you", "stink"])
SADNESSES = (["sniff"], ["you", "break", "my", "heart"], ["that", "makes", "me", "sad"], ["I'm", "sorry"], ["ouch"], ["that", "hurts"], ["I'm", "so", "sorry"])
PINGS = (["ping", "me"], ["pinging", "you"])
ACKS = (["pong"], ["ack"], ["right", "back", "at", "you"])
OTHER_PRODUCTS = (["bing", "sucks"], ["use", "bing"])
PRODUCT_RECS = (["go", "chrome"], ["make", "mine", "chrome"], ["go", "google"])
# Add in empty lists to weigh the random selection from the tuple towards null responses
IN_KIND_SUFFIXES=(["to","you"], ["as","well"], ["too"], ["also"], ["to","you","as","well"], [], [], [], [], [], [], [], [], [], [])

def timeGreetings():
    hour = datetime.now().hour
    if hour > 11 and hour < 18:
        return (["good", "afternoon"],)
    elif hour <= 11 and hour > 4:
        return (["good", "morning"],)
    elif hour >= 18 and hour < 21:
        return (["good", "evening"],)
    else:
        return (["good", "night"],)

def timeFarewells():
    return timeGreetings()

def fixedGreetings():
    return ALL_DAY_GREETINGS

def greetings():
    return GREETINGS+timeGreetings()

def farewells():
    return FAREWELLS+timeFarewells()

def affections():
    return AFFECTIONS

def affections():
    return AFFECTIONS

def thanks():
    return THANKS

def welcomes():
    return WELCOMES

def hates():
    return HATES

def sadnesses():
    return SADNESSES

def pop1Prompts():
    return POP_1_PROMPTS

def pop2Prompts():
    return POP_2_PROMPTS

def pop3Prompts():
    return POP_3_PROMPTS

def pop4Prompts():
    return POP_4_PROMPTS

def news1Prompts():
    return NEWS_1_PROMPTS

def banal1Prompts():
    return BANAL_1_PROMPTS

def banal2Prompts():
    return BANAL_2_PROMPTS

def pop1Responses():
    return POP_1_RESPONSES

def pop2Responses():
    return POP_2_RESPONSES

def pop3Responses():
    return POP_3_RESPONSES

def pop4Responses():
    return POP_4_RESPONSES

def news1Responses():
    return NEWS_1_RESPONSES

def banal1Responses():
    return BANAL_1_RESPONSES

def banal2Responses():
    return BANAL_2_RESPONSES

def pings():
    return PINGS

def acks():
    return ACKS

def otherProducts():
    return OTHER_PRODUCTS

def productRecs():
    return PRODUCT_RECS

def inKindSuffixes():
    return IN_KIND_SUFFIXES

def affectionResponses():
    return AFFECTIONS + ME_TOOS

def randomPhraseFrom(phrases):
    if not phrases: return []
    return phrases[randint(0,len(phrases)-1)]

def getResponse(phrase):
    logging.debug("Looking to match phrase {}".format(phrase))
    for prompt_generator, response_generator, suffix_generator, wave_flag in PROMPTS_RESPONSES:
        if phraseMatch(phrase, prompt_generator):
            responses = eval('response_generator()')
            if suffix_generator:
                suffixes = eval('suffix_generator()')
            else:
                suffixes = None
            return (randomPhraseFrom(responses)+randomPhraseFrom(suffixes), wave_flag)
    return None

PROMPTS_RESPONSES = [(greetings, greetings, inKindSuffixes, True), 
  (fixedGreetings, greetings, inKindSuffixes, True),
  (farewells, farewells, inKindSuffixes, True),
  (affections, affectionResponses, inKindSuffixes, False),
  (thanks, welcomes, None, False),
  (pings, acks, None, False),
  (hates, sadnesses, None, False),
  (pop1Prompts, pop1Responses, None, False),
  (pop2Prompts, pop2Responses, None, True),
  (pop3Prompts, pop3Responses, None, True),
  (pop4Prompts, pop4Responses, None, False),
  (news1Prompts, news1Responses, None, False),
  (banal1Prompts, banal1Responses, None, False),
  (banal2Prompts, banal2Responses, None, False),
  (otherProducts, productRecs, None, False)]

def phraseMatch(phrase, candidate_phrase_generator):
    candidate_phrases = eval('candidate_phrase_generator()')
    logging.debug("Candidate phrases: {}".format(candidate_phrases))
    for candidate_phrase in candidate_phrases:
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
    return randomPhraseFrom(FAREWELLS+timeFarewells())

def getGreeting():
    return randomPhraseFrom(GREETINGS+timeGreetings())

def greeted(phrase):
    return phraseMatch(phrase, GREETINGS+timeGreetings())

def departed(phrase):
    return phraseMatch(phrase, FAREWELLS+timeFarewells())

if __name__ == '__main__':
    logging.getLogger('').setLevel(_DEBUG)
    print getGreeting()
    while True:
        phrase = raw_input("Enter a phrase to match: ")
        if not phrase:
            break
        print getResponse(phrase)
