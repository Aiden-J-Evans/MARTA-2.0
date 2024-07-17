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
        A python list of the objects.
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

    messages = [
        {"role": "user",
          "content": "What are some very simple background objects which stand on the ground that would make sense for this story: \"" + story + "\" Return the 1-word objects in a python list."}
    ]

    output = pipe(messages, **generation_args)
    list_string = output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()
    del output, model, tokenizer, pipe, generation_args
    gc.collect()
    torch.cuda.empty_cache()
    return eval(list_string)

def find_possible_background(story):
    """
    Uses Microsoft Phi to decide a background setting for the entire story.

    Args:
        story (str): the entire story

    Returns:
        A string of the estimated setting.
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

    messages = [
        {"role": "user",
          "content": "What is a very simple location setting which would make sense for this story: \"" + story + "\" Return only 1 word."}
    ]

    output = pipe(messages, **generation_args)
    string = output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()
    torch.cuda.empty_cache()
    del output, model, tokenizer, pipe, generation_args
    gc.collect()
    return str(string)


