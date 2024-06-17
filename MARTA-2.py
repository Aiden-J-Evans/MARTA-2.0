from rendering.start_render import render
from audio.audio_generation import generate_audio
import spacy
from transformers import pipeline
from transformers import AutoModelForCausalLM, AutoTokenizer

prompt = input("Please enter your story (End with a period): ")
nlp = spacy.load("en_core_web_sm")
doc = nlp(prompt)

#sentence container
sentences = []
# current sentence
current = []

# organize sentences
for token in doc:
    if str(token) == ".":
        sentences.append(current)
        current = []
    else:
        current.append(token)

# determines if an animation is needed or not
classifier = pipeline("zero-shot-classification")
# the threshold (between 0 and 1) which determines whether an action should be preformed
ACTION_THRESHOLD = 0.9
CHARACTER_THRESHOLD = 0.9

for sentence_tokens in sentences:
    # get setence (without period)
    sentence = ' '.join([str(token) for token in sentence_tokens])
    
    #generate audio based on the sentence
    #generate_audio(sentence, 5)
    
    
    # uses a transformer
    action_score = classifier(str(sentence), ["action"])["scores"][0]
    actions = [str(token) for token in sentence_tokens if token.pos_ == "VERB" and action_score > ACTION_THRESHOLD]
    characters = [str(token) for token in sentence_tokens if token.pos_ == "PROPN" and classifier(str(token), ["person"])["scores"][0] > CHARACTER_THRESHOLD]
    objects = [str(token) for token in sentence_tokens if token.pos_ == "NOUN" or token.pos_ == "PROPN" and classifier(str(token), ["physical object"])["scores"][0] > CHARACTER_THRESHOLD]

    print(characters, objects, actions)

    for character in characters:
        print(character)
    for action in actions:
        print([action])
    for obj in objects:
        print(obj)



#render()

