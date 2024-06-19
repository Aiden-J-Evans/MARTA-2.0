from openai import OpenAI



def ask_gpt(prompt):
    """
    Asks gpt-3.5-turbo a question

    Args:
        prompt (str): the input prompt for chat-gpt

    Returns:
        Chat-gpt's response
    """
    client = OpenAI()

    stream = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            response += chunk.choices[0].delta.content

    return response

def estimate_sentence_length(sentence):
    """
    Returns the estimated spoken length of the sentence. Averages higher times.
    
    Args:
        sentence (str): The input sentence you want to estimate

    Returns:
        An integer based on the length of the sentence
    """
    return round((len(sentence.split()) / 100) * 60)