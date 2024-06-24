# Load model directly
from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained("microsoft/Phi-3-mini-4k-instruct", trust_remote_code=True)
input_text = "What is your name?"

# Tokenize input text
input_ids = tokenizer.encode(input_text, return_tensors="pt")

# Generate text
output = model.generate(input_ids, max_length=50, num_return_sequences=1, no_repeat_ngram_size=2, early_stopping=True)

# Decode the generated sequence
generated_text = tokenizer.decode(output[0], skip_special_tokens=True)

print(generated_text)

def estimate_sentence_length(sentence):
    """
    Returns the estimated spoken length of the sentence. Averages higher times.
    
    Args:
        sentence (str): The input sentence you want to estimate

    Returns:
        An integer based on the length of the sentence
    """
    return round((len(sentence.split()) / 100) * 60)