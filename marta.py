from rendering.start_render import render
from nlp.nlp_manager import *
from texture_generation.stable import generate_image
from audio.audio_generation import generate_audio, generate_voiceover
from rendering.momask_utils import create_animation

from spacy import load
from transformers import pipeline
import json, torch, os

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

from nlp.nlp_manager import *
from texture_generation.stable import generate_image
import os
story = "David was a young shepherd. Goliath was a giant warrior. David used a sling to throw a stone. The stone hit Goliath on the forehead. David celebrates joyfully while Goliath lay slain on the ground."
file_paths = {
    "setting_image_path": "background.png",
    "floor_image_path": "floor.png",
    "ceiling_image_path": "ceiling.png"
}

# prompts functions
prompts_functions = {
    "setting_image_path": get_background_prompt,
    "floor_image_path": get_floor_prompt,
    "ceiling_image_path": get_ceiling_prompt
}

# generate and save images
for key, filename in file_paths.items():
    image_path = os.path.join(os.getcwd(), "texture_generation", "generated_images", filename)
    generate_image(prompts_functions[key](story), image_path, width=1536 if filename == 'background.png' else 512)
    timeline[key] = image_path

# determines if an animation is needed or not
classifier = pipeline("zero-shot-classification", device="cuda" if torch.cuda.is_available() else "cpu", model="facebook/bart-large-mnli")



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
    currrent_characters = [str(token) for token in sentence_tokens if token.pos_ == "PROPN" and classifier(str(token), ["character"])["scores"][0] > CHARACTER_THRESHOLD]

    character_dict = {}
    if currrent_characters:
        for index, character in enumerate(currrent_characters):
            if character not in all_characters:
                all_characters.append(character)
            else: # if the character has already been mentioned, move to most recent in the list
                all_characters.remove(character)
                all_characters.append(character)

            if actions and index < len(actions):
                character_dict[character.lower()] = {'animation':create_animation(prompt=get_animation_prompt(sentence, character, story), length=sequence_length)}
            else:
                character_dict[character.lower()] = {'animation': 'idle'}       
    elif actions: # this gives the last action to the most recent character to be metioned if no characters were metioned in this sentence
        character_dict[all_characters[-1].lower()] = {'animation':create_animation(prompt=get_animation_prompt(sentence, character, story), length=sequence_length)}
    else:
        for character in all_characters:
            character_dict[character.lower()] = {'animation':'idle'}

    # if characters are not mentioned in the current sentence, set their animation to idle
    for character in set(all_characters) - set(currrent_characters):
        character_dict[character.lower()] = {'animation': 'idle'}

    # saves the frames
    timeline[str(next_frame)] = {'audio_paths': [background_audio_path, tts_audio_path], 'characters': character_dict}
    next_frame += sequence_length * 30



timeline['end_frame'] = next_frame
with open('frame_data.json', 'w', encoding='utf-8') as f:
    json.dump(timeline, f, ensure_ascii=False, indent=4)
#render()

