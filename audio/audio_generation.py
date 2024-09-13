from transformers import AutoProcessor, MusicgenForConditionalGeneration
import os, scipy
from gtts import gTTS
# use musicgen-small,medium


def generate_audio(index, prompt, length=10, story_name="default") -> str:
  """
  Generates an audioclip using a transformer
  
  Args:
    prompt (str): the prompt given to the model.
    length (int): the length of the audioclip in seconds.

  Returns:
    The path to the audio file
  """
  
  processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
  model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
  inputs = processor(
      text=[prompt],
      padding=True,
      return_tensors="pt",
  )

  print("Generating music for \"" + prompt + "\"")
  audio_values = model.generate(**inputs, max_new_tokens = round(length*51.2))
  print("Done generating music for \"" + prompt + "\"")

  sampling_rate = model.config.audio_encoder.sampling_rate

  path = os.path.join(os.getcwd(), "audio", "generated_audio", story_name, "background" + str(index) + ".wav")

  scipy.io.wavfile.write(path, rate=sampling_rate, data=audio_values[0, 0].numpy())

  return path

def generate_voiceover(index=int, sentence=str, story_name=str) -> str:
  """
  Generates an audio clip narrating the given sentence.

  Args:
    index (int): the index of the sentence in the story (used for saving location)
    sentence (str): the given sentence to be narrated

  Returns:
    The path to the generated audio.
  """
  print("Generating voiceover...")
  tts = gTTS(text=sentence, lang='en')
  path = os.path.join(os.getcwd(),  "audio", "generated_audio", story_name, "speech" + str(index) + ".mp3") 
  tts.save(path)
  return path



