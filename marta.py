from rendering.start_render import render
from nlp.nlp_manager import estimate_sentence_length, find_possible_background
from spacy import load
import json, torch, os
from transformers import pipeline

story = input("Please enter your story (End with a period): ")
#voiceover_enabled = input("Would you like a voice over? (Y/n)") == 'Y'
nlp = load("en_core_web_sm")
doc = nlp(story)

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


# the threshold (between 0 and 1) which determines whether an action should be preformed
ACTION_THRESHOLD = 0.75
CHARACTER_THRESHOLD = 0.9

# vars for json
timeline = {}
next_frame = 1
all_characters = []

torch.cuda.empty_cache()
from texture_generation.stable import generate_image
setting_image_path = generate_image(find_possible_background(story))

timeline['setting_image_path'] = os.path.join(os.getcwd(), "texture_generation", "background.png") #setting_image_path

# determines if an animation is needed or not
classifier = pipeline("zero-shot-classification", device="cuda" if torch.cuda.is_available() else "cpu", model="facebook/bart-large-mnli")

from audio.audio_generation import generate_audio, generate_voiceover
from rendering.momask_utils import create_animation

for i, sentence_tokens in enumerate(sentences):
    # get setence (without period)
    sentence = ' '.join([str(token) for token in sentence_tokens])
    print("Working on:", sentence)
    # estimates sentence length based on an equation
    sequence_length = estimate_sentence_length(sentence)
    
    #generate background and speech audio based on the sentence
    background_audio_path = generate_audio(i, sentence, sequence_length)
    tts_audio_path = generate_voiceover(i, sentence)
    
    # uses a transformer to estimate sentence similarity
    action_score = classifier(str(sentence), ["physical action"])["scores"][0]
    actions = [str(token.lemma_) for token in sentence_tokens if token.pos_ == "VERB" and action_score > ACTION_THRESHOLD]
    characters = [str(token) for token in sentence_tokens if token.pos_ == "PROPN" and classifier(str(token), ["person"])["scores"][0] > CHARACTER_THRESHOLD]

    character_dict = {}
    if len(characters) != 0:
        for index, character in enumerate(characters):
            if character not in all_characters:
                all_characters.append(character)
            else:
                all_characters.remove(character)
                all_characters.append(character)
            if len(actions) != 0 and index < len(actions):
                character_dict[character.lower()] = {'animation':create_animation(prompt=actions[index], length=sequence_length)}
            else:
                character_dict[character.lower()] = {'animation': 'idle'}       
    elif len(actions) != 0:
        character_dict[all_characters[-1].lower()] = {'animation':create_animation(prompt=actions[0], length=sequence_length)}
    else:
        character_dict[all_characters[-1].lower()] = {'animation':'idle'}

    # saves the frames
    timeline[str(next_frame)] = {'audio_paths': [background_audio_path, tts_audio_path], 'characters': character_dict}
    next_frame += sequence_length * 30



timeline['end_frame'] = next_frame
with open('frame_data.json', 'w', encoding='utf-8') as f:
    json.dump(timeline, f, ensure_ascii=False, indent=4)
render()

