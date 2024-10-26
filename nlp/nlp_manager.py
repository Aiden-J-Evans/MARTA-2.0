"""
Author: Aiden
NOTE: 
- use torch.random.seed() for random asset generation
- use torch.random.manual_seed() for reproducing asset generation
"""

from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch, gc

def estimate_sentence_length(sentence : str) -> int:
    """
    Returns the estimated spoken length of the sentence. Averages higher times.
    
    Args:
        sentence (str): The input sentence you want to estimate

    Returns:
        An integer based on the length of the sentence
    """
    return round((len(sentence.split()) / 100) * 32) + 1

###########################################################################
# Code taken from https://huggingface.co/microsoft/Phi-3-mini-4k-instruct #
###########################################################################

def get_object_list(story : str) -> list:
    """
    Uses Microsoft Phi to decide acceptable objects to be generated for the story.
    Currently not in use.
    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        A python list containing possible objects.
    """

    torch.random.seed()

    model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", 
            device_map="cuda", 
            torch_dtype="auto", 
            trust_remote_code=True, 
        )

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

    pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    generation_args = {
            "max_new_tokens": 500,
            "return_full_text": False,
            "temperature": 0.0,
            "do_sample": False,
        }

    object_prompt = "What are some very simple background objects which stand on the ground that would make sense for this story: \"" + story + "\" Return the 1-word objects in a python list."

    obj_message = [
        {"role": "user", "content" : object_prompt},
    ]

    obj_output = pipe(obj_message, **generation_args)
    list_string = obj_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    gc.collect()
    torch.cuda.empty_cache()

    try:
        output = eval(list_string)
        return [output]
    except:
        print("Generated object list was not in the correct format. Run MARTA again.")

# NOTE: With Phi-3, hallucinations are possible. You can see this when the prompt is passed to MoMask

def get_background_prompt(story : str) -> str:
    """
    Uses Microsoft Phi to decide acceptable objects to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        The string prompt for the background image.
    """
    torch.random.seed()

    model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", 
            device_map="cuda", 
            torch_dtype="auto", 
            trust_remote_code=True, 
        )

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

    pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    generation_args = {
            "max_new_tokens": 500,
            "return_full_text": False,
            "temperature": 0.1,
            "do_sample": True,
        }
    background_prompt = "Create a prompt for generating a detailed background image based on the setting described in: \"" + story + "\". The prompt should focus on the environment, capturing the mood and atmosphere without including characters or objects. Ensure the final prompt is concise and suitable for an image generator and less than 77 tokens."
    setting_message = [
        {"role": "user", "content" : background_prompt},
    ]

    setting_output = pipe(setting_message, **generation_args)
    setting = setting_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    gc.collect()
    torch.cuda.empty_cache()
    return str(setting)

def get_animation_prompt(sentence : str, character : str) -> str:
    """
    Uses Microsoft Phi to decide acceptable animations to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted
        character (str): the character that the animation is for
    Returns:
        The string prompt for the background animation.
    """
    torch.random.seed()

    model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", 
            device_map="cuda", 
            torch_dtype="auto", 
            trust_remote_code=True, 
        )

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

    pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    generation_args = {
            "max_new_tokens": 500,
            "return_full_text": False,
            "temperature": 0.1,
            "do_sample": True,
        }
    
    action_prompt = "Generate a simple and clear action prompt for an AI human motion generator.  The action should be appropriate for the character: " + character + " based on the context provided in this sentence: \"" + sentence + "\". If there is an appropriate action for the character, return only the action prompt without punctuation. If no clear action is suitable, return the word 'idle'." # and with the characters replaced with \"a person\""
    action_message = [
        {"role": "user", "content" : action_prompt},
    ]

    action_output = pipe(action_message, **generation_args)
    action = action_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    gc.collect()
    torch.cuda.empty_cache()
    return str(action)

def get_floor_prompt(story : str) -> str:
    """
    Uses Microsoft Phi to decide an acceptable floor prompt for the story.

    Args:
        story (str): the entire story

    Returns:
        A string prompt for the image generator.
    """
    torch.random.seed()

    model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", 
            device_map="cuda", 
            torch_dtype="auto", 
            trust_remote_code=True, 
        )

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

    pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    generation_args = {
            "max_new_tokens": 77,
            "return_full_text": False,
            "temperature": 0.1,
            "do_sample": True,
        }
    
    ground_prompt = "Create a 1 word prompt (such as 'grass' or 'gravel') for generating a floor texture based on the setting described in: \"" + story + "\". The prompt should focus on the environment, capturing the mood and atmosphere without including characters or objects. Ensure the final prompt is concise and suitable for an image generator and less than 77 tokens."

    ground_message = [
        {"role": "user", "content" : ground_prompt},
    ]

    ground_output = pipe(ground_message, **generation_args)
    ground = ground_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    gc.collect()
    torch.cuda.empty_cache()
    print(ground)
    return str(ground)

def get_audio_prompt(sentence, story):
    """
    Uses Microsoft Phi to decide acceptable objects to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        The string prompt for the background image.
    """
    torch.random.seed()

    model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", 
            device_map="cuda", 
            torch_dtype="auto", 
            trust_remote_code=True, 
        )

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-medium-4k-instruct")

    pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    generation_args = {
            "max_new_tokens": 500,
            "return_full_text": False,
            "temperature": 0.1,
            "do_sample": True,
        }
    background_prompt = "What is a simple prompt that can be given to an AI audio generator in this story: \"" + story + "\" for this specific sentence sentence: \"" + sentence + "\" You should return the prompt so that it can be read as a python string. It should describe the type or style of music that fits the sentence."
    setting_message = [
        {"role": "user", "content" : background_prompt},
    ]

    setting_output = pipe(setting_message, **generation_args)
    setting = setting_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    gc.collect()
    torch.cuda.empty_cache()
    print(setting)
    return str(setting)

def get_ceiling_prompt(story : str) -> str:
    """
    Uses Microsoft Phi to decide an acceptable ceiling prompt for the story.

    Args:
        story (str): the entire story

    Returns:
        A string prompt for the image generator.
    """
    torch.random.seed()

    model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", 
            device_map="cuda", 
            torch_dtype="auto", 
            trust_remote_code=True, 
        )

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

    pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    generation_args = {
            "max_new_tokens": 77,
            "return_full_text": False,
            "temperature": 0.1,
            "do_sample": True,
        }
    
    ceiling_prompt = "Create a prompt for generating a detailed sky image based on the setting described in: \"" + story + "\". The prompt should focus on the environment, capturing the mood and atmosphere without including characters or objects. Ensure the final prompt is concise and suitable for an image generator and less than 77 tokens."

    ceiling_message = [
        {"role": "user", "content" : ceiling_prompt},
    ]

    ceiling_output = pipe(ceiling_message, **generation_args)
    ceiling = ceiling_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    gc.collect()
    torch.cuda.empty_cache()

    return str(ceiling)

# TODO: find a way to make this better. position estimation is not perfect
def get_next_movement(current_sentence : str, current_character : str, story : str, character_positions : dict, animation_name : str) -> list:
    """
    Uses Microsoft Phi to decide acceptable character movement for the story.

    Args:
        current_sentence (str): the entirity of the current sentence
        current_character (str): the name of the character whose position we want to predict
        story (str): the entire story whose background objects will be interpreted
        character_positions (dict): the entirity of all character positions throughout the story to this point
        animation_name (str): the description of the animation, used in the prompt
    Returns:
        A length 3 list of x, y, z coordinate (z coordinate is not used)
    """
    torch.random.seed()

    model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct", 
            device_map="cuda", 
            torch_dtype="auto", 
            trust_remote_code=True, 
        )

    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

    pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

    generation_args = {
            "max_new_tokens": 500,
            "return_full_text": False,
            "temperature": 0.0,
            "do_sample": False,
        }
    
    position_prompt = "You must hypothesize the position that the character will move to by the end of the sentence. For context, the entire story is \"" + story + "\". The current character is: " + current_character + ". The current sentence is: \"" + current_sentence + "\" The name of the animation the character performs over this sentence is: " + animation_name + ". For more context, here are the previous vector coordinates of this character and the other characters in the story: " + "".join([name + ": " + "".join([str(p) + "," for p in positions]) for name, positions in character_positions.items()]) + ". Provide the new estimated Vector position for the character in a python tuple. It should only be the tuple, no other tokens. If you fail to provide a response that python can evaluate, the program will fail. Also ensure that different characters are not in the same position."
    position_message = [
        {"role": "user", "content" : position_prompt},
    ]

    position_output = pipe(position_message, **generation_args)
    new_positon = position_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    gc.collect()
    torch.cuda.empty_cache()
    return eval(new_positon)

