import bpy
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import os
# use musicgen-small,medium


def generate_audio(prompt="", length=10):
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

  audio_values = model.generate(**inputs, max_new_tokens = round(length*51.2))

  import scipy

  sampling_rate = model.config.audio_encoder.sampling_rate
  audio_name = prompt + ".wav"

  scipy.io.wavfile.write(prompt + ".wav", rate=sampling_rate, data=audio_values[0, 0].numpy())

  return os.getcwd() + "\\" + audio_name

