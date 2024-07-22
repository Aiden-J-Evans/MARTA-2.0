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



def find_possible_objects(story):
    """
    Uses Microsoft Phi to decide acceptable objects to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        A python list containing a list of objects [0] and a string setting [1].
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
    return [eval(list_string), str(setting)]

def find_possible_background(story):
    """
    Uses Microsoft Phi to decide acceptable objects to be generated for the story.

    Args:
        story (str): the entire story whose background objects will be interpreted

    Returns:
        A python list containing a list of objects [0] and a string setting [1].
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
    background_prompt = "What is a detailed prompt for an AI image generator with the task of generating a background image relating to this story's location: \"" + story + "\" Don't include any characters or objects in the prompt, it should be the setting only. It also has to be less than 77 tokens."
    setting_message = [
        {"role": "user", "content" : background_prompt},
    ]

    setting_output = pipe(setting_message, **generation_args)
    setting = setting_output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()

    del model, tokenizer, pipe, generation_args, setting_output
    gc.collect()
    torch.cuda.empty_cache()
    return str(setting)