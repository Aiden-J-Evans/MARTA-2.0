# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

def estimate_sentence_length(sentence):
    """
    Returns the estimated spoken length of the sentence. Averages higher times.
    
    Args:
        sentence (str): The input sentence you want to estimate

    Returns:
        An integer based on the length of the sentence
    """
    return round((len(sentence.split()) / 100) * 60)

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

    messages = [
        {"role": "user",
          "content": "What are some very simple background objects which stand on the ground that would make sense for this story: \"" + story + "\" Return the 1-word objects in a python list."}
    ]

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

    output = pipe(messages, **generation_args)
    list_string = output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()
    return eval(list_string)

def find_possible_background(story):
    torch.random.manual_seed(0)

    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/Phi-3-mini-4k-instruct", 
        device_map="cuda", 
        torch_dtype="auto", 
        trust_remote_code=True, 
    )
    tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")

    messages = [
        {"role": "user",
          "content": "What is a very simple location setting which would make sense for this story: \"" + story + "\" Return only 1 word."}
    ]

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

    output = pipe(messages, **generation_args)
    string = output[0]['generated_text'].replace('```python\n', '').replace('\n```', '').strip()
    return str(string)

print(find_possible_background("David was a shepherd boy who lived in Israel.  One day a giant named Goliath started bragging to his soldier friends that none of the Israelites would dare to fight him. The Israelite soldiers were all afraid of the giant Goliath. The King of Israel Saul was also unable to stop him. That’s when little David decided to face Goliath himself. He went and got some stones and a slingshot to combat the Giant. The giant ridiculed David. But he went in with all his faith. He took a stone and put it in his sling and flung it at Goliath. The stone hit Goliath on the forehead and he fell to the ground immediately. Then David killed him with his sword. All the Philistines ran away and Israel was protected. The faithful shepherd boy had saved the Jewish people with the help of the Lord."))