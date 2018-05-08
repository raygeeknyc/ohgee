# BUG - single list tuples below raise an error in getResponse()
import logging
_DEBUG=logging.INFO
_DEBUG=logging.DEBUG

import os
from random import randint
from datetime import datetime
from google.cloud.language.entity import EntityType

POP_1_PROMPTS = (["who", "is", "the", "man"], ["who", "would", "risk", "his", "neck"], ["his", "neck", "for", "his", "brother", "man"], ["the", "cat", "that", "won't", "cop", "out", "when"], ["danger", "all", "about"] )
POP_1_RESPONSES = (["SHAFT"], ["that's", "shaft"], ["john", "shaft"])

POP_2_PROMPTS = (["is", "a", "bad", "mother"], ["they", "say", "this", "shaft", "is"])
POP_2_RESPONSES = (["shut", "your", "mouth"], ["shut", "your", "mouth"])

POP_3_PROMPTS = (["talking", "about", "shaft"], ["talking", "bout", "shaft"])
POP_3_RESPONSES = (["we", "can", "dig", "it"], ["dig", "it"], ["right", "on"])

POP_4_PROMPTS = (["shut", "your", "mouth"], ["shut", "your", "mouth"])
POP_4_RESPONSES = (["hey", "I'm", "talking", "about", "shaft"], ["hey", "I'm", "talkin", "bout", "shaft"])

NEWS_1_PROMPTS = (["president" ,"trump"], ["donald", "trump"])
NEWS_1_RESPONSES = (["Trump", "is", "a", "chump"], ["donald", "chump"], ["dump", "trump"])

FRIENDS_3_PROMPTS = (["I'm", "nilma"], ["I", "am", "nilma"], ["this", "is", "nilma"])
FRIENDS_3_RESPONSES = (["I'm", "so", "glad", "to", "meet", "you", "nilma"], ["I've", "heard", "so", "much", "about", "you", "nilma"], ["Raymond", "says", "such", "good", "things", "about", "you", "nilma"])

FRIENDS_1_PROMPTS = (["I'm", "diana"], ["I", "am", "diana"], ["this", "is", "diana"])
FRIENDS_1_RESPONSES = (["I'm", "so", "glad", "to", "meet", "you", "diana"], ["I've", "heard", "so", "much", "about", "you", "diana"], ["Raymond", "says", "such", "good", "things", "about", "you", "diana"])

FRIENDS_2_PROMPTS = (["I'm", "jillian"], ["I", "am", "jillian"], ["this", "is", "jillian"])
FRIENDS_2_RESPONSES = (["what", "a", "pleasure", "to", "meet", "you", "jillian"], ["set", "the", "world", "on", "fire", "jillian"], ["I'm", "so", "happy", "to", "finally", "meet", "jillian"])

ID_PROMPTS = (["who", "are", "you"], ["what", "is", "your", "name"], ["what", "are", "you"])
ID_RESPONSES = (["I", "am", "oh", "jee", ",", "a", "desktop", "robot", "friend"], ["my", "name", "is", "oh", "jee"], ["I", "am", "oh", "jee"], ["hello", "I'm", "oh", "jee"])

INTRO_PROMPTS = (["I", "am"], ["my", "name", "is"], ["hello", "i'm"], ["this", "is"])
INTRO_RESPONSES = (["hi"], ["hello"], ["it's", "good", "to", "see", "you"], ["i'm", "glad", "to", "know", "you"], ["hey", "there"])

CANINE_PROMPTS = (["good", "puppy"], ["nice", "puppy"], ["good", "dog"], ["nice", "doggy"], ["nice", "doggie"], ["Who's", "a", "good", "doggy"], ["Who's", "a", "good", "dog"], ["Who's", "a", "good", "girl"], ["Who's", "a", "good", "boy"])
CANINE_RESPONSES = (["woof", "woof"], ["you're", "a", "very", "good", "dog"])

FELINE_PROMPTS = (["good", "kitty"], ["nice", "kitty"], ["good", "kitten"], ["nice", "kitten"], ["good", "cat"], ["nice", "cat"])
FELINE_RESPONSES = (["meow"], ["meow", "meow"], ["purr", "purr", "purr"], ["petunia", "is", "a", "good", "girl"])

BANAL_1_PROMPTS = (["you", "know", "what"], ["guess", "what"])
BANAL_1_RESPONSES = (["what?"],["no", "what?"])

GIRLS_COUNT_PROMPTS = (["what's", "the", "number"], ["the", "number", "is", "what", "now"], ["the", "numbers", "what", "now"])
GIRLS_COUNT_RESPONSES = (["fourteen", "thousand", "two hundred", "and", "ninety six"], ["14", "2", "9", "6"])

BANAL_2_PROMPTS = (["how's", "the", "weather"], ["hows", "the", "weather"], ["what's", "the", "weather"], ["whats", "the", "weather"], ["how", "is", "the", "weather"], ["what", "is", "the", "weather"])
BANAL_2_RESPONSES = (["chili", "today", "hot", "ta-ma-lay"], ["chili", "today", "but", "hot", "ta-ma-lay"])

GREETINGS = ( ["happy", "national", "robot", "week"], ["o", "la"], ["always", "a", "pleasure"], ["Its", "good", "to", "see", "you"], ["hello"], ["hi"], ["hey", "there"], ["nice", "to", "see", "you"], ["good", "to", "see", "you"], ["welcome"], ["good", "day"], ["good", "day", "to", "you"], ["oh", "hello"], ["yay", ",", "it's", "you"], ["I", "love", "being", "a", "robot"])
ALL_DAY_GREETINGS = (["good", "morning"], ["good", "afternoon"], ["good", "evening"], ["good", "night"])
FAREWELLS = (["goodbye"], ["bye"], ["farewell"], ["see","you"], ["talk", "to", "you", "later"], ["take", "care"], ["bye", "bye"], ["see", "you", "later"], ["later"], ["call", "me"], ["did", "you", "just", "sign", "out?"], ["come", "back","soon"])
SMUGS = (["I'm", "the", "best"], ["I", "am", "the", "best"], ["Who's", "better", "than", "me"], ["I", "love", "me"], ["I", "love", "myself"])
SMUG_RESPONSES = (["that", "makes", "one", "of", "you"], ["Who", "are", "you", "again"], ["oh", "you", "snowflake"])
AFFECTIONS = (["you're", "adorable"], ["I", "adore", "you"], ["I", "love", "you"], ["I", "like", "you"], ["you're", "the", "best"], ["you're", "cute"], ["you're", "so", "cute"], ["you're", "sweet"], ["you're", "so", "sweet"], ["you're", "cool"], ["you're", "great"], ["cute", "robot"], ["you're", "awesome"], ["you're", "amazing"], ["I", "really", "like", "you"], ["I", "think", "you're", "fantastic"])
ME_TOOS = (["I", "feel", "the", "same"], ["that", "makes", "two", "of", "us"], ["I", "feel", "the", "same", "way"], ["same", "here"])
THANKS = (["thank", "you"], ["thanks"], ["why", "thank", "you"], ["thank", "you", "so", "much"])
WELCOMES = (["you're", "welcome"], ["don't", "mention", "it"], ["day", "nada"], ["my", "pleasure"], ["no", "worries"])
HATES = (["I", "hate", "you"], ["I", "don't", "like", "you"], ["you", "suck"], ["you're", "stupid"], ["you're", "awful"], ["stupid", "robot"], ["dumb", "robot"], ["you", "stink"])
SADNESSES = (["sniff"], ["you", "break", "my", "heart"], ["that", "makes", "me", "sad"], ["I'm", "sorry"], ["ouch"], ["that", "hurts"], ["I'm", "so", "sorry"])
JOKE_PROMPTS = (["knock", "knock"], ["knock", "knock"])
JOKE_RESPONSES = (["I", "don't", "know", "who's", "there"], ["you", "get", "it"], ["it's", "for", "you"])
JOKE_2_PROMPTS = (["why", "did", "the", "chicken", "cross", "the", "road"], 
["why", "did", "the", "chicken", "cross", "the", "road"])
JOKE_2_RESPONSES = (["to", "get", "david", "hassle", "hoff's", "autograph"], ["because", ",", "she", "was", "on", "the", "wrong", "side"])
PINGS = (["ping", "me"], ["pinging", "you"])
ACKS = (["pong"], ["ack"], ["right", "back", "at", "you"])
TIME_PROMPTS = (["what", "time", "is", "it"], ["what's", "the", "time"])
DATE_PROMPTS = (["what", "day", "is", "it"], ["what's", "today's", "date"], ["what's", "the", "date"], ["what", "day", "is", "today"], ["what", "is", "today"], ["what's", "today"])
OTHER_PRODUCTS = (["bing", "sucks"], ["use", "bing"])
PRODUCT_RECS = (["go", "chrome"], ["make", "mine", "chrome"], ["go", "google"])
# Add in empty lists to weigh the random selection from the tuple towards null responses
IN_KIND_SUFFIXES=(["to","you"], ["as","well"], ["too"], ["also"], ["to","you","as","well"], ["yourself"], [], [], [], [], [], [], [], [], [], [])

MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

DOW = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def idResponses(entities):
    return ID_RESPONSES

def introResponses(entities):
    address = randomPhraseFrom(INTRO_RESPONSES)
    return (address + getPerson(entities),)

def timeResponses(_):
    hour = datetime.now().hour
    minute = datetime.now().minute
    return (["its", "now", str(hour), str(minute)],)
    
def dateResponses(_):
    month = MONTH[datetime.now().month-1]
    day = datetime.now().day
    dow = DOW[datetime.weekday(datetime.now())]
    return (["today", "is", dow, month, str(day)],)

def timeGreetings(_):
    hour = datetime.now().hour
    if hour > 11 and hour < 18:
        return (["good", "afternoon"],)
    elif hour <= 11 and hour > 4:
        return (["good", "morning"],)
    elif hour >= 18 and hour < 21:
        return (["good", "evening"],)
    else:
        return (["good", "night"],)

def timeFarewells(_):
    return timeGreetings(None)

def fixedGreetings(_):
    return ALL_DAY_GREETINGS

def greetings(_):
    return GREETINGS+timeGreetings(None)

def farewells(_):
    return FAREWELLS+timeFarewells(None)

def affections(_):
    return AFFECTIONS

def thanks(_):
    return THANKS

def welcomes(_):
    return WELCOMES

def hates(_):
    return HATES

def sadnesses(_):
    return SADNESSES

def pop1Prompts(_):
    return POP_1_PROMPTS

def pop2Prompts(_):
    return POP_2_PROMPTS

def pop3Prompts(_):
    return POP_3_PROMPTS

def pop4Prompts(_):
    return POP_4_PROMPTS

def news1Prompts(_):
    return NEWS_1_PROMPTS

def friends1Prompts(_):
    return FRIENDS_1_PROMPTS

def friends2Prompts(_):
    return FRIENDS_2_PROMPTS

def friends3Prompts(_):
    return FRIENDS_3_PROMPTS

def caninePrompts(_):
    return CANINE_PROMPTS

def felinePrompts(_):
    return FELINE_PROMPTS

def smugPrompts(_):
    return SMUGS

def banal1Prompts(_):
    return BANAL_1_PROMPTS

def idPrompts(_):
    return ID_PROMPTS

def introPrompts(_):
    return INTRO_PROMPTS

def girlsCountPrompts(_):
    return GIRLS_COUNT_PROMPTS

def banal2Prompts(_):
    return BANAL_2_PROMPTS

def pop1Responses(_):
    return POP_1_RESPONSES

def pop2Responses(_):
    return POP_2_RESPONSES

def pop3Responses(_):
    return POP_3_RESPONSES

def pop4Responses(_):
    return POP_4_RESPONSES

def news1Responses(_):
    return NEWS_1_RESPONSES

def girlsCountResponses(_):
    return GIRLS_COUNT_RESPONSES

def friends1Responses(_):
    return FRIENDS_1_RESPONSES

def friends2Responses(_):
    return FRIENDS_2_RESPONSES

def friends3Responses(_):
    return FRIENDS_3_RESPONSES

def canineResponses(_):
    return CANINE_RESPONSES

def felineResponses(_):
    return FELINE_RESPONSES

def smugResponses(_):
    return SMUG_RESPONSES

def banal1Responses(_):
    return BANAL_1_RESPONSES

def banal2Responses(_):
    return BANAL_2_RESPONSES

def timePrompts(_):
    return TIME_PROMPTS

def datePrompts(_):
    return DATE_PROMPTS

def jokePrompts(_):
    return JOKE_PROMPTS

def jokeResponses(_):
    return JOKE_RESPONSES

def joke2Prompts(_):
    return JOKE_2_PROMPTS

def joke2Responses(_):
    return JOKE_2_RESPONSES

def pings(_):
    return PINGS

def acks(_):
    return ACKS

def otherProducts(_):
    return OTHER_PRODUCTS

def productRecs(_):
    return PRODUCT_RECS

def inKindSuffixes(_):
    return IN_KIND_SUFFIXES

def affectionResponses(_):
    return AFFECTIONS + ME_TOOS

def randomPhraseFrom(phrases):
    if not phrases: return []
    return phrases[randint(0,len(phrases)-1)]

def getPerson(entities):
    if not entities:
        return [""]
    salience = 0
    person = ""
    for entity in entities:
        if entity.entity_type == EntityType.PERSON:
          if entity.salience > salience:
            salience = entity.salience
            person = entity.name
    return [person]

def getResponse(phrase, entities):
    logging.debug("Looking to match phrase {}".format(phrase))
    for prompt_generator, response_generator, suffix_generator, wave_flag in PROMPTS_RESPONSES:
        if phraseMatch(phrase, entities, prompt_generator):
            responses = eval('response_generator(entities)')
            if suffix_generator:
                suffixes = eval('suffix_generator(entities)')
            else:
                suffixes = None
            return (randomPhraseFrom(responses)+randomPhraseFrom(suffixes), wave_flag)
    return None

PROMPTS_RESPONSES = [
  (smugPrompts, smugResponses, None, False),
  (felinePrompts, felineResponses, None, True),
  (caninePrompts, canineResponses, None, True),
  (pop1Prompts, pop1Responses, None, False),
  (pop2Prompts, pop2Responses, None, True),
  (friends1Prompts, friends1Responses, None, True),
  (friends2Prompts, friends2Responses, None, True),
  (friends3Prompts, friends3Responses, None, True),
  (idPrompts, idResponses, None, False),
  (introPrompts, introResponses, None, False), # This should follow specific intros
  (greetings, greetings, inKindSuffixes, True), 
  (fixedGreetings, greetings, inKindSuffixes, True),
  (farewells, farewells, inKindSuffixes, True),
  (affections, affectionResponses, inKindSuffixes, False),
  (thanks, welcomes, None, True),
  (pings, acks, None, False),
  (jokePrompts, jokeResponses, None, True),
  (joke2Prompts, joke2Responses, None, True),
  (hates, sadnesses, None, False),
  (timePrompts, timeResponses, None, False),
  (datePrompts, dateResponses, None, False),
  (pop3Prompts, pop3Responses, None, True),
  (pop4Prompts, pop4Responses, None, False),
  (news1Prompts, news1Responses, None, False),
  (girlsCountPrompts, girlsCountResponses, None, False),
  (banal1Prompts, banal1Responses, None, False),
  (banal2Prompts, banal2Responses, None, False),
  (otherProducts, productRecs, None, False)]

def phraseMatch(phrase, entities, candidate_phrase_generator):
    candidate_phrases = eval('candidate_phrase_generator(entities)')
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
    return randomPhraseFrom(FAREWELLS+timeFarewells(None))

def getGreeting():
    return randomPhraseFrom(GREETINGS+timeGreetings(None))

def greeted(phrase):
    return phraseMatch(phrase, GREETINGS+timeGreetings(None))

def departed(phrase):
    return phraseMatch(phrase, FAREWELLS+timeFarewells(None))

if __name__ == '__main__':
    logging.getLogger('').setLevel(_DEBUG)
    print getGreeting()
    while True:
        phrase = raw_input("Enter a phrase to match: ")
        if not phrase:
            break
        print getResponse(phrase, None)
