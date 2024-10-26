"""
Author: Aiden
NOTE: 
- You can either use a pre-trained model, or a python library based on Google translate for voiceover audio
"""
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import os, scipy

def generate_audio(index: int, prompt: str, length=10, story_name="default") -> str:
  """
  Generates an audioclip using a transformer
  
  Args:
    index (int): the sentence index of the background audio
    prompt (str): the prompt given to the model.
    length (int): the length of the audioclip in seconds.
    story_name (str): the name of the story for organizational purposes
  Returns:
    The path to the audio file
  """
  
  # use musicgen-small or musicgen-medium
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

def model_generate_voiceover(index=int, sentence=str, story_name=str) -> str:
  """
  Generates an audio clip narrating the given sentence.

  Args:
    index (int): the index of the sentence in the story (used for saving location)
    sentence (str): the given sentence to be narrated
    story_name (str): the name of the story for organizational purposes
  Returns:
    The path to the generated audio.
  """
  print("Generating voiceover...")

  # code taken from https://huggingface.co/microsoft/speecht5_tts

  from transformers import pipeline
  from datasets import load_dataset
  import soundfile as sf
  import torch

  
  synthesiser = pipeline("text-to-speech", "microsoft/speecht5_tts", device="cuda" if torch.cuda.is_available() else "cpu")
  embeddings_dataset = load_dataset("Matthijs/cmu-arctic-xvectors", split="validation")

  # change the index of embedding_dataset for different voices
  speaker_embedding = torch.tensor(embeddings_dataset[1024]["xvector"]).unsqueeze(0)
  

  speech = synthesiser(f"{sentence}.", forward_params={"speaker_embeddings": speaker_embedding})

  path = os.path.join(os.getcwd(),  "audio", "generated_audio", story_name, "speech" + str(index) + ".mp3") 
  sf.write(path, speech["audio"], samplerate=speech["sampling_rate"])
  return path

def generate_tts_voiceover(index=int, sentence=str, story_name=str) -> str:
  """
  Generates an audio clip narrating the given sentence.

  Args:
    index (int): the index of the sentence in the story (used for saving location)
    sentence (str): the given sentence to be narrated
    story_name (str): the name of the story for organizational purposes
  Returns:
    The path to the generated audio.
  """
  from gtts import gTTS

  print("Generating voiceover...")
  tts = gTTS(text=sentence, lang='en')
  path = os.path.join(os.getcwd(),  "audio", "generated_audio", story_name, "speech" + str(index) + ".mp3") 
  tts.save(path)
  return path
