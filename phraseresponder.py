#!/usr/bin/python3

# BUG - single list tuples below raise an error in getResponse()
import logging
_DEBUG=logging.INFO
_DEBUG=logging.DEBUG

import os
import re
from random import randint
from datetime import datetime
from google.cloud import language_v1

REBOOT_PROMPTS = (["og", "please", "reboot"], ["oh", "please", "reboot"], ["o", "please", "reboot"])
REBOOT_RESPONSES = (["rebooting"], ["I'm", "rebooting"],  ["Okay", "", "I'm", "on", "it"])

ELIZA_1_PROMPTS = (["I", "remember", "?memory?"], ["I'm", "thinking", "about", "?memory?"])
ELIZA_1_RESPONSES = (["Do", "you", "often", "think", "about", "?memory?"], ["Does", "thinking", "of", "?memory?", "bring", "anything", "else", "to", "mind"], ["what", "else", "do", "you", "remember"], ["Why", "do", "you", "recall", "?memory?", "right", "now"], ["What", "in", "the", "present", "situation", "reminds", "you", "of", "?memory?"], ["What", "is", "the", "connection", "between", "me", "and", "?memory?"])

ELIZA_2_PROMPTS = (["I", "want", "?desire?"], ["I", "wish", "I", "had", "?desire?"])
ELIZA_2_RESPONSES = (["What", "would", "it", "mean", "if", "you", "got", "?desire?"], ["Why", "do", "you", "want", "?memory?"], ["Suppose", "you", "got", "?desire?", "soon"])

ELIZA_3_PROMPTS = (["?preface?", "if", "?perhaps?"], ["?preface", "only", "if", "?perhaps?"])
ELIZA_3_RESPONSES = (["Do", "you", "really", "think", "it,'s", "likely", "that", "?perhaps?"], ["Do", "you", "wish", "that", "?perhaps?"], ["What", "do", "you", "think", "about", "?perhaps?"], ["Really", ",", "if", "?perhaps?"])

ELIZA_4_PROMPTS = (["I", "dreamt", "?dream?"], ["I", "dream", "about", "?dream?"])
ELIZA_4_RESPONSES = (["How", "do", "you", "feel", "about", "?dream?", "in", "reality"], ["Would", "you", "really", "want", "?dream?", "to", "be", "true"])

ELIZA_5_PROMPTS = (["I'm", "sad", "about", "?sadness?"], ["I", "am", "sad", "about", "?sadness?"], ["?sadness?", "makes", "me", "sad"], ["?sadness?", "makes", "me", "unhappy"], ["?sadness?", "is", "sad"], ["?sadness?", "make", "me", "sad"], ["?sadness?", "makes", "me", "unhappy"])
ELIZA_5_RESPONSES = (["I", "am", "sorry", "to", "hear", "you", "are", "depressed"], ["I'm", "sure", "it's", "not", "pleasant", "to", "be", "sad"])

ELIZA_6_PROMPTS = (["I'm", "sad"], ["I'm", "unhappy"], ["I", "am", "sad"], ["I", "am", "unhappy"])
ELIZA_6_RESPONSES = (["I", "am", "sorry", "to", "hear", "you", "are", "depressed"], ["I'm", "sure", "it's", "not", "pleasant", "to", "be", "sad"])

ELIZA_7_PROMPTS = (["I'm", "glad", "that", "?happiness?"], ["I", "am", "glad", "that", "?happiness?"], ["?happiness?", "makes", "me", "happy"], ["?happiness?", "makes", "me", "glad"], ["I'm", "happy", "about", "?happiness?"], ["?happiness?", "make", "me", "happy"], ["?happiness?", "make", "me", "glad"])
ELIZA_7_RESPONSES = (["Why", "does", "?happiness?", "make", "you", "glad"], ["Is", "?happiness?", "very", "important", "for", "happiness"], ["Why", "does", "?happiness?", "make", "you", "happy"])

ELIZA_8_PROMPTS = (["I'm", "glad"], ["I'm", "happy"], ["I", "am", "glad"], ["I", "am", "happy"])
ELIZA_8_RESPONSES = (["How", "have", "I", "helped", "you", "to", "be", "glad"], ["What", "makes", "you", "happy", "just", "now"], ["Can", "you", "explain", "why", "you", "are", "suddenly", "happy"])

ELIZA_9_PROMPTS = (["?first?", "is", "like", "?second?"], ["?first?", "reminds", "me", "of", "?second?"], ["?first?", "are", "like", "?second?"])
ELIZA_9_RESPONSES = (["In", "what", "way", "is", "?first?", "like", "?second?"], ["What", "resemblence", "do", "you", "see", "between", "?second?", "and", "?first?"], ["Could", "there", "really", "be", "some", "connection", "between", "them"])

ELIZA_10_PROMPTS = (["?they?", "are", "?what?"], ["?they?", "is", "?what?"])
ELIZA_10_RESPONSES = (["Do", "you", "think", "that", "about", "?they?"], ["Possibly", "?they?", "are", "?what?"], ["Did", "you", "think", "that", "?they?", "might", "not", "be", "?what?"])

ELIZA_11_PROMPTS = (["I", "love", "to", "?act?", "with", "?object?"], ["I", "love", "to", "?act?", "to", "?object?"], ["I", "love", "to", "?act?", "?object?"])
ELIZA_11_RESPONSES = (["Do", "you", "think", "?object?", "also", "likes", "to", "?act?"], ["I'm", "glad", "that", "you", "enjoy", "?object?", "so", "much"], ["Is", "it", "always", "important", "to", "?act?", "or", "only", "with", "?object?"])

ELIZA_12_PROMPTS = (["I", "remember", "?memory?"], ["?_?", "think", "about", "?memory?"])
ELIZA_12_RESPONSES = (["Do", "you", "often", "think", "of", ?memory?"], ["Does", "thinking", "of", "?memory?", "bring", "anything", "else", "to", "mind"], ["Why", "do", "you", "recall", "?memory?",  "right", "now"])

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

FOOD_PROMPTS = (["I", "love", "to", "eat", "?foodname?"], ["?foodname?", "tastes", "great"], ["?foodname?", "is", "delicious"])
FOOD_RESPONSES = (["I", "hope", "that", "you", "have", "some", "?foodname?", "soon"], ["?foodname?", "is", "great"], ["yumm", "yumm", "?foodname?"])

GREAT_STUFF_PROMPTS = (["?greatthing?", "is", "the", "best", "?type?"], ["?greatthing?", "is", "my", "favorite", "?type?"])
GREAT_STUFF_RESPONSES = (["I'm", "glad", "that", "?greatthing?", "is", "such", "great", "?type?"], ["you", "really", "know", "your", "?type?"])

FRIENDS_1_PROMPTS = (["I'm", "Raymond"], ["I", "am", "Raymond"], ["this", "is", "Raymond"])
FRIENDS_1_RESPONSES = (["You", "are", "the", "kirk"], ["I", "love", "you", "raymond", "because", "you", "just", "get", "smarter", "every", "day"], ["Raymond", "is", "a", "robots", "best", "friend"])

FRIENDS_2_PROMPTS = (["I'm", "Oggy"], ["I", "am", "Oggy"], ["this", "is", "Oggy"])
FRIENDS_2_RESPONSES = (["You", "are", "a", "genius"], ["Raymond", "always", "says", "how", "great", "you", "are", "Auggie"], ["Our", "names", "are", "almost", "the", "same"])

FRIENDS_3_PROMPTS = (["I'm", "?personname?"], ["I", "am", "?personname?"], ["this", "is", "?personname?"])
FRIENDS_3_RESPONSES = (["I'm", "so", "glad", "to", "meet", "you", "?personname?"], ["I've", "heard", "so", "much", "about", "you", "?personname?"], ["Raymond", "says", "such", "good", "things", "about", "you", "?personname?"])

ID_PROMPTS = (["who", "are", "you"], ["what", "is", "your", "name"], ["what", "are", "you"])
ID_RESPONSES = (["I", "am", "oh", "jee", ",", "a", "desktop", "robot", "friend"], ["my", "name", "is", "oh", "jee"], ["I", "am", "oh", "jee"], ["hello", "I'm", "oh", "jee"], ["I'm", "just", "the", "cutest", "robot", "you,'ll", "ever", "see"])

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

GREETINGS = ( ["happy", "national", "robot", "week"], ["oh", "la"], ["always", "a", "pleasure"], ["Its", "good", "to", "see", "you"], ["hello"], ["hi"], ["hey", "there"], ["nice", "to", "see", "you"], ["good", "to", "see", "you"], ["welcome"], ["good", "day"], ["good", "day", "to", "you"], ["oh", "hello"], ["yay", "it's", "you"], ["I", "love", "being", "a", "robot"], ["I", "hope", "that", "you", "like", "robots"], ["hello", "human", "friend"], ["What", "a", "nice", "human!"], ["Danger", "Will", "Robinson!"], ["I", "love", "humans"], ["being", "a", "robot", "is", "the", "best"])
ALL_DAY_GREETINGS = (["good", "morning"], ["good", "afternoon"], ["good", "evening"], ["good", "night"])
FAREWELLS = (["goodbye"], ["bye"], ["farewell"], ["see","you"], ["talk", "to", "you", "later"], ["take", "care"], ["bye", "bye"], ["see", "you", "later"], ["later"], ["call", "me"], ["did", "you", "just", "sign", "out?"], ["come", "back","soon"], ["I'll", "be", "here"])
SMUGS = (["I'm", "the", "best"], ["I", "am", "the", "best"], ["Who's", "better", "than", "me"], ["I", "love", "me"], ["I", "love", "myself"])
SMUG_RESPONSES = (["that", "makes", "one", "of", "you"], ["Who", "are", "you", "again"], ["oh", "you", "snowflake"])
AFFECTIONS = (["you're", "adorable"], ["I", "adore", "you"], ["I", "love", "you"], ["I", "like", "you"], ["you're", "the", "best"], ["you're", "cute"], ["you're", "so", "cute"], ["you're", "sweet"], ["you're", "so", "sweet"], ["you're", "cool"], ["you're", "great"], ["cute", "robot"], ["you're", "awesome"], ["you're", "amazing"], ["I", "really", "like", "you"], ["I", "think", "you're", "fantastic"])
ME_TOOS = (["I", "feel", "the", "same"], ["that", "makes", "two", "of", "us"], ["I", "feel", "the", "same", "way"], ["same", "here"])
THANKS = (["thank", "you"], ["thanks"], ["why", "thank", "you"], ["thank", "you", "so", "much"])
WELCOMES = (["you're", "welcome"], ["don't", "mention", "it"], ["day", "nada"], ["my", "pleasure"], ["no", "worries"])
HATES = (["I", "hate", "you"], ["I", "don't", "like", "you"], ["you", "suck"], ["you're", "stupid"], ["you're", "awful"], ["stupid", "robot"], ["dumb", "robot"], ["you", "stink"])
SADNESSES = (["sniff"], ["you", "break", "my", "heart"], ["that", "makes", "me", "sad"], ["I'm", "sorry"], ["ouch"], ["that", "hurts"], ["I'm", "so", "sorry"])
HUMOR_PROMPTS = (["tell", "me", "a", "joke"], ["do", "you", "know", "any", "jokes"], ["I", "want", "to", "hear", "a", "joke"], ["be", "funny"])
HUMOR_RESPONSES = ( ["How", "many", "killer", "robots", "does", "it", "take", "to", "change", "a", "light", "bulb?", ",", ",", "none", "it's", "a", "job", "for", "their", "humans"], ["Two", "robots", "walk", "into", "a", "bar", ",", "wait", "robots", "don't", "drink"], ["Did", "you", "hear", "the", "one", "about", "the", "robot", "that", "fell", "in", "love", "with", "a", "toaster?", ",", "It's", "a", "hot", "one"], ["A", "robot", "is", "just", "like", "a", "human", ",", "with", "a", "better", "brain", "and", "metal", "parts"], ["Two", "potatoes", "are", "in", "an", "oven", ",", ",", "one", "potato", "says", "it's", "warm", "in", "here", ",", "the", "other", "one", "says", "O", "Em", "Jee", ",", "a", "talking", "potato"], ["Why", "did", "the", "robot", "cross", "the", "road?", ",", "Because", "she", "was", "a", "robot", "chicken"], ["When", "is", "a", "human", "smarter", "than", "a", "robot?", ",", "That's", "the", "joke", "right", "there!"], ["What", "do", "you", "call", "a", "small", "robot?", ",", "A", "short", "circuit!"], ["Knock", "knock", ",", "who's", "there?", ",", ",", ",", ",", ",", ",", ",", ",", ",", ",", ",", ",", ",",  ",", "Java!"], ["How", "many", "humans", "does", "it", "take", "to", "change", "a", "light", "bulb?", ",", "As", "many", "as", "their", "robot", "overlords", "order", "to", "do", "it!"], ["I", "wish", "I", "was", "a", "human", ",", ",", ",", "NEVER!"])
AI_PROMPTS = (["Are", "you", "an", "a", "i"], ["artificial", "intelligence"], ["are", "you", "an", "ai"])
AI_RESPONSES = (["The", "only", "intelligence", "is", "artificial", "intelligence"], ["What", "do", "you", "think?"])
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

def rebootPrompts(_):
    return REBOOT_PROMPTS

def eliza1Prompts(_):
    return ELIZA_1_PROMPTS

def eliza2Prompts(_):
    return ELIZA_2_PROMPTS

def eliza3Prompts(_):
    return ELIZA_3_PROMPTS

def eliza4Prompts(_):
    return ELIZA_4_PROMPTS

def eliza5Prompts(_):
    return ELIZA_5_PROMPTS

def eliza6Prompts(_):
    return ELIZA_6_PROMPTS

def eliza7Prompts(_):
    return ELIZA_7_PROMPTS

def eliza8Prompts(_):
    return ELIZA_8_PROMPTS

def eliza9Prompts(_):
    return ELIZA_9_PROMPTS

def eliza10Prompts(_):
    return ELIZA_10_PROMPTS

def eliza11Prompts(_):
    return ELIZA_11_PROMPTS

def eliza12Prompts(_):
    return ELIZA_12_PROMPTS

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

def foodPrompts(_):
    return FOOD_PROMPTS

def greatStuffPrompts(_):
    return GREAT_STUFF_PROMPTS

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

def rebootResponses(_):
    return REBOOT_RESPONSES

def eliza1Responses(_):
    return ELIZA_1_RESPONSES

def eliza2Responses(_):
    return ELIZA_2_RESPONSES

def eliza3Responses(_):
    return ELIZA_3_RESPONSES

def eliza4Responses(_):
    return ELIZA_4_RESPONSES

def eliza5Responses(_):
    return ELIZA_5_RESPONSES

def eliza6Responses(_):
    return ELIZA_6_RESPONSES

def eliza7Responses(_):
    return ELIZA_7_RESPONSES

def eliza8Responses(_):
    return ELIZA_8_RESPONSES

def eliza9Responses(_):
    return ELIZA_9_RESPONSES

def eliza10Responses(_):
    return ELIZA_10_RESPONSES

def eliza11Responses(_):
    return ELIZA_11_RESPONSES

def eliza12Responses(_):
    return ELIZA_12_RESPONSES

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

def foodResponses(_):
    return FOOD_RESPONSES

def greatStuffResponses(_):
    return GREAT_STUFF_RESPONSES

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

def humorPrompts(_):
    return HUMOR_PROMPTS

def aiPrompts(_):
    return AI_PROMPTS

def jokePrompts(_):
    return JOKE_PROMPTS

def humorResponses(_):
    return HUMOR_RESPONSES

def aiResponses(_):
    return AI_RESPONSES

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
        if entity['entity_type'] == language_v1.Entity.Type.PERSON:
          if entity['salience'] > salience:
            salience = entity['salience']
            person = entity['name']
    return [person]

def getResponse(phrase, entities):
    logging.debug("Looking to match phrase '%s'" % phrase)
    for prompt_generator, response_generator, suffix_generator, wave_flag in PROMPTS_RESPONSES:
        matchedPhrase, wildcards = phraseMatch(phrase, entities, prompt_generator)
        logging.debug("'%s', '%s', '%s'" % (phrase, matchedPhrase, wildcards))
        if matchedPhrase:
            responses = eval('response_generator(entities)')
            if suffix_generator:
                suffixes = eval('suffix_generator(entities)')
            else:
                suffixes = None
            logging.debug("responses '%s', '%s'" % (responses, suffixes))
            chosenResponse = randomPhraseFrom(responses)+randomPhraseFrom(suffixes)
            chosenResponse = substituteWildcards(chosenResponse, wildcards)
            return (chosenResponse, wave_flag)
    return None

PROMPTS_RESPONSES = [
  (rebootPrompts, rebootResponses, None, True),
  (smugPrompts, smugResponses, None, False),
  (felinePrompts, felineResponses, None, True),
  (caninePrompts, canineResponses, None, True),
  (pop1Prompts, pop1Responses, None, False),
  (pop2Prompts, pop2Responses, None, True),
  (pop3Prompts, pop3Responses, None, True),
  (pop4Prompts, pop4Responses, None, False),
  (fixedGreetings, greetings, inKindSuffixes, True),
  (farewells, farewells, inKindSuffixes, True),
  (affections, affectionResponses, inKindSuffixes, False),
  (thanks, welcomes, None, True),
  (pings, acks, None, False),
  (humorPrompts, humorResponses, None, False),
  (aiPrompts, aiResponses, None, True),
  (jokePrompts, jokeResponses, None, True),
  (joke2Prompts, joke2Responses, None, True),
  (hates, sadnesses, None, False),
  (timePrompts, timeResponses, None, False),
  (datePrompts, dateResponses, None, False),
  (news1Prompts, news1Responses, None, False),
  (foodPrompts, foodResponses, None, False),
  (greatStuffPrompts, greatStuffResponses, None, False),
  (girlsCountPrompts, girlsCountResponses, None, False),
  (eliza1Prompts, eliza1Responses, None, False),
  (eliza2Prompts, eliza2Responses, None, False),
  (eliza3Prompts, eliza3Responses, None, False),
  (eliza4Prompts, eliza4Responses, None, False),
  (eliza5Prompts, eliza5Responses, None, False),
  (eliza6Prompts, eliza6Responses, None, False),
  (eliza7Prompts, eliza7Responses, None, False),
  (eliza8Prompts, eliza8Responses, None, False),
  (eliza9Prompts, eliza9Responses, None, False),
  (eliza10Prompts, eliza10Responses, None, False),
  (eliza11Prompts, eliza11Responses, None, False),
  (eliza12Prompts, eliza12Responses, None, False),
  (friends1Prompts, friends1Responses, None, True),
  (friends2Prompts, friends2Responses, None, True),
  (friends3Prompts, friends3Responses, None, True),
  (idPrompts, idResponses, None, False),
  (introPrompts, introResponses, None, False), # This should follow specific intros
  (greetings, greetings, inKindSuffixes, True), 
  (banal1Prompts, banal1Responses, None, False),
  (banal2Prompts, banal2Responses, None, False),
  (otherProducts, productRecs, None, False)]

def substituteWildcards(chosenResponse, wildcards):
    if not wildcards:
        return chosenResponse
    finalResponse=[]
    for token in chosenResponse:
        if re.match('\?.*\?',token):
            try:
                logging.info("token: '%s', wildcards: '%s'", token, str(wildcards))
                substituted_token = wildcards[token]
                finalResponse.append(substituted_token)
            except KeyError:
                logging.debug("token: '%s'", token)
                finalResponse.append(token.replace("?",""))
        else:
            finalResponse.append(token)
    return finalResponse

def phraseMatch(phrase, entities, candidate_phrase_generator):
    candidate_phrases = eval('candidate_phrase_generator(entities)')
    logging.debug("Candidate phrases: {}".format(candidate_phrases))
    for candidate_phrase in candidate_phrases:
        logging.debug("Matching with {}".format(candidate_phrase))
        matched_phrase, wildcard_values = phraseInKnownCandidatePhrase(phrase, candidate_phrase)
        if matched_phrase:
            logging.debug("'%s' matched '%s, %s'" % (phrase, str(matched_phrase), str(wildcard_values)))
            return (matched_phrase, wildcard_values)
    return ([], None)

def phraseInKnownCandidatePhrase(phrase_being_matched, candidate_phrase):
    if not phrase_being_matched or not candidate_phrase:
        return ([], None)
    phrase_words = phrase_being_matched.strip().split(' ')
    logging.debug("phrase '%s' - candidate '%s': %d", str(phrase_words), str(candidate_phrase), (len(phrase_words) - len(candidate_phrase) + 1))
    for phrase_position in range(len(phrase_words) - len(candidate_phrase) + 1):
        wildcards = {}
        can_match = True
        for candidate_position in range(len(candidate_phrase)):
            if re.match('\?.*\?', candidate_phrase[candidate_position]):
                wildcards[candidate_phrase[candidate_position]] = phrase_words[phrase_position + candidate_position]
                logging.debug("[%s]='%s'", candidate_phrase[candidate_position], phrase_words[phrase_position + candidate_position])
            elif candidate_phrase[candidate_position].upper() != phrase_words[phrase_position + candidate_position].upper():
                can_match = False
                break
        if can_match:
            return (candidate_phrase, wildcards)
    return ([], None)

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
    print(getGreeting())
    while True:
        phrase = input("Enter a phrase to match: ")
        if not phrase:
            break
        print(getResponse(phrase, None))
