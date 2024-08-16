# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch, gc

def estimate_sentence_length(sentence):
    """
    Returns the estimated spoken length of the sentence. Averages higher times.
    
    Args:
        sentence (str): The input sentence you want to estimate

    Returns:
        An integer based on the length of the sentence
    """
    return round((len(sentence.split()) / 100) * 60)

###########################################################################
# Code taken from https://huggingface.co/microsoft/Phi-3-mini-4k-instruct #
###########################################################################

def get_object_list(story):
    """
    Uses Microsoft Phi to decide acceptable objects to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        A python list containing possible objects.
    """

    torch.random.manual_seed(0)

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
    background_prompt = "What is a detailed prompt for an AI image generator with the task of generating a background image relating to this story's location: \"" + story + "\" Don't include any characters or objects in the prompt, it should be the setting only. It also has to be less than 77 tokens."

    obj_message = [
        {"role": "user", "content" : object_prompt},
    ]

    setting_message = [
        {"role": "user", "content" : background_prompt},
    ]

    obj_output = pipe(obj_message, **generation_args)
    list_string = obj_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    setting_output = pipe(setting_message, **generation_args)
    setting = setting_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    del obj_output, model, tokenizer, pipe, generation_args, setting_output
    gc.collect()
    torch.cuda.empty_cache()

    try:
        output = eval(list_string)
        return [output, str(setting)]
    except:
        print("Generated object list was not in the correct format. Run MARTA again.")

    
def get_background_prompt(story):
    """
    Uses Microsoft Phi to decide acceptable objects to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        The string prompt for the background image.
    """
    torch.random.manual_seed(0)

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
    background_prompt = "What is a detailed prompt for an AI image generator with the task of generating a background image relating to this story's location: \"" + story + "\" Don't include any characters or objects in the prompt, it should be the setting only. It also has to be less than 77 tokens."
    setting_message = [
        {"role": "user", "content" : background_prompt},
    ]

    setting_output = pipe(setting_message, **generation_args)
    setting = setting_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    del model, tokenizer, pipe, generation_args, setting_output
    gc.collect()
    torch.cuda.empty_cache()
    print(setting)
    return str(setting)

def get_animation_prompt(sentence : str, character : str, story : str):
    """
    Uses Microsoft Phi to decide acceptable animations to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        The string prompt for the background animation.
    """
    torch.random.manual_seed(0)

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
    
    action_prompt = "What is a very simple prompt for an AI humanoid action generator with the task of generating an action for: " + character + " in this sentence: \"" + sentence + "\". Here is the entire story for futher context: \"" + story + "\". If there is no suitable animation, return with 'idle'. If there is a suitable animation, return only the prompt with no punctuation" # and with the characters replaced with \"a person\""
    setting_message = [
        {"role": "user", "content" : action_prompt},
    ]

    action_output = pipe(setting_message, **generation_args)
    action = action_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    del model, tokenizer, pipe, generation_args, action_output
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
    torch.random.manual_seed(0)

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
    
    ground_prompt = "What is a simple prompt for an AI image generator with the task of generating a floor texture relating to this story: \"" + story + "\" The prompt should only concern the floor texture. There should be no buildings, it should only concern the floor."

    ground_message = [
        {"role": "user", "content" : ground_prompt},
    ]

    ground_output = pipe(ground_message, **generation_args)
    ground = ground_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    del model, tokenizer, pipe, generation_args, ground_output
    gc.collect()
    torch.cuda.empty_cache()
    print(ground)
    return str(ground)

def get_ceiling_prompt(story : str) -> str:
    """
    Uses Microsoft Phi to decide an acceptable ceiling prompt for the story.

    Args:
        story (str): the entire story

    Returns:
        A string prompt for the image generator.
    """
    torch.random.manual_seed(0)

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
    
    ceiling_prompt = "What is a simple prompt for an AI image generator with the task of generating a sky texture relating to this story: \"" + story + "\" The prompt should only concern the sky texture. There should be no buildings, it should only concern the sky. It should be from the point of view of someone looking directly up at the sky."

    ceiling_message = [
        {"role": "user", "content" : ceiling_prompt},
    ]

    ceiling_output = pipe(ceiling_message, **generation_args)
    ceiling = ceiling_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    del model, tokenizer, pipe, generation_args, ceiling_output
    gc.collect()
    torch.cuda.empty_cache()

    return str(ceiling)

def get_next_movement(current_sentence : str, current_character : str, story : str, character_positions : dict, animation_name : str) -> tuple:
    """
    Uses Microsoft Phi to decide acceptable character movement for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        The string prompt for the background image.
    """
    torch.random.manual_seed(0)

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
    
    position_prompt = "You must hypothesize the position that the character will move to by the end of the sentence. For context, the entire story is \"" + story + "\". The current character is: " + current_character + ". The current sentence is: \"" + current_sentence + "\" The name of the animation the character performs over this sentence is: " + animation_name + ". For more context, here are the previous vector coordinates of this character and the other characters in the story: " + "".join([name + ": " + "".join([str(p) + "," for p in positions]) for name, positions in character_positions.items()]) + ". Provide the new estimated Vector position for the character in a python tuple based on the animation. It should only be the tuple, no other tokens. If you fail to provide a response that python can evaluate, the program will fail."
    print(position_prompt)
    position_message = [
        {"role": "user", "content" : position_prompt},
    ]

    position_output = pipe(position_message, **generation_args)
    new_positon = position_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    del model, tokenizer, pipe, generation_args, position_output
    gc.collect()
    torch.cuda.empty_cache()
    return eval(new_positon)
