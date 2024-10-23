from rendering.start_render import render
from nlp.nlp_manager import *
from texture_generation.stable import generate_image
from audio.audio_generation import generate_audio, generate_voiceover
from rendering.momask_utils import *

from spacy import load
from transformers import pipeline
import json, torch, os

def set_idle_animation(character_dict : dict, character_positions : dict, character : str, length: int, story_name : str, index : int):
    """
    Sets a character's animation data to the idle values
    
    Args:
        character_dict (dict): the dictionary containing all current characters in the story
        character_positions (dict): the dictionary containing all end positions at specific sentences for the story
        character (str): The name of the character (lowercase)
    """
    last_position = character_positions.get(character, [(len(character_positions), 0, 0)])[-1]
    character_dict[character] = {'animation': create_idle(length, story_name=story_name, index=index), 'sequence_end_position': last_position}
    character_positions.setdefault(character, []).append(last_position)
    
def set_generated_animation(story: str, character_dict : dict, character_positions : dict, sentence : str, character : str, sequence_length : int, story_name: str):
    """
    Sets a character's animation data its generated values
    
    Args:
        story (str): the entire story for context
        character_dict (dict): the dictionary containing all current characters in the story
        character_positions (dict): the dictionary containing all end positions at specific sentences for the story
        sentence (str): the current sentence
        character (str): The name of the character (lowercase)
        sequence_length (int): the estimated number of frames in the current sentence
    """
    animation_prompt = get_animation_prompt(sentence, character, story)
    position = get_next_movement(sentence, character, story, character_positions, animation_prompt)
    animation_path = create_animation(prompt=animation_prompt, length=sequence_length, story_name=story_name)
    character_dict[character] = {'animation': animation_path, 'sequence_end_position': position}
    character_positions.setdefault(character, [(len(character_positions), 0, 0)]).append((position[0], position[1], 0))
    print(f"Sequence length: {sequence_length}")

def create_directories(story_name):
    """Creates all the directories for the specific story.
    
    Args:
        story_name (str): the given name of the story.
    """
    os.makedirs(os.path.join(os.getcwd(), "audio", "generated_audio", story_name), exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), "rendering", "animations", story_name), exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), "texture_generation", "generated_images", story_name), exist_ok=True)
    os.makedirs(os.path.join(os.getcwd(), "output", story_name), exist_ok=True)
    

story_name = input("Please enter your story's name: ")
story = input("Please enter your story (End with a period): ")
quality = input("What would you like the quality of your render to be? (low, med, high, best) ")
save_file = True if input("Would you like to save the .blend file? (Y/n) ").strip().lower() == "y" else False
nlp = load("en_core_web_sm")
doc = nlp(story)

create_directories(story_name)

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
    image_path = os.path.join(os.getcwd(), "texture_generation", "generated_images", story_name, filename)
    generate_image(prompts_functions[key](story), image_path, width=1536 if filename == 'background.png' else 512, story_name=story_name)
    timeline[key] = image_path

# determines if an animation is needed or not
classifier = pipeline("zero-shot-classification", device="cuda" if torch.cuda.is_available() else "cpu", model="facebook/bart-large-mnli")


character_positions = {}
idle_index = 0
for i, sentence_tokens in enumerate(sentences):
    # get setence (without period)
    sentence = ' '.join([str(token) for token in sentence_tokens])
    print("Working on:", sentence)
    # estimates sentence length based on an equation
    sequence_length = estimate_sentence_length(sentence)
    
    #generate background and speech audio based on the sentence
    audio_prompt = get_audio_prompt(sentence, story)
    background_audio_path = generate_audio(i, audio_prompt, sequence_length, story_name)
    tts_audio_path = generate_voiceover(i, sentence, story_name)
    
    # uses a transformer to estimate sentence similarity
    action_score = classifier(str(sentence), ["physical action"])["scores"][0]
    actions = [str(token.lemma_) for token in sentence_tokens if token.pos_ == "VERB" and action_score > ACTION_THRESHOLD]
    currrent_characters = [str(token).lower() for token in sentence_tokens if token.pos_ == "PROPN" and classifier(str(token), ["character"])["scores"][0] > CHARACTER_THRESHOLD]

    character_dict = {}
    if currrent_characters:
        for index, character in enumerate(currrent_characters):
            if character not in all_characters:
                all_characters.append(character)
            else: # if the character has already been mentioned, move to most recent in the list
                all_characters.remove(character)
                all_characters.append(character)

            if actions and index < len(actions):
                set_generated_animation(story, character_dict, character_positions, sentence, character, sequence_length, story_name)
            else:
                set_idle_animation(character_dict, character_positions,character, sequence_length, story_name, idle_index)
                idle_index += 1

    elif actions: # this gives the last action to the most recent character to be metioned if no characters were metioned in this sentence
        character = all_characters[-1]
        set_generated_animation(story, character_dict, character_positions, sentence, character, sequence_length, story_name)
        idle_index += 1
    else:
        for character in all_characters:
            set_idle_animation(character_dict, character_positions, character, sequence_length, story_name, idle_index)
            idle_index += 1

    # if characters are not mentioned in the current sentence, set their animation to idle
    for character in set(all_characters) - set(currrent_characters):
        set_idle_animation(character_dict, character_positions, character, sequence_length, story_name, idle_index)
        idle_index += 1

    # saves the frames
    timeline[str(next_frame)] = {'audio_paths': [background_audio_path, tts_audio_path], 'characters': character_dict}
    next_frame += sequence_length * 32



timeline['render_quality'] = quality.lower().strip()
timeline['render_output'] = os.path.join(os.getcwd(), "output", story_name, story_name + ".mp4")
timeline['blender_output'] = os.path.join(os.getcwd(), "output", story_name, story_name + ".blend") if save_file else ""
timeline['end_frame'] = next_frame
frame_data_path = os.path.join(os.getcwd(), "output", story_name, story_name.replace(" ", "_") + "_frame_data.json")
with open(frame_data_path, 'w', encoding='utf-8') as f:
    json.dump(timeline, f, ensure_ascii=False, indent=4)
render(frame_data_path)

