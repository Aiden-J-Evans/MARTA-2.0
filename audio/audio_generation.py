from transformers import pipeline
from IPython.display import Audio
import numpy as np
import bpy # type: ignore
from pydub import AudioSegment
# use musicgen-small,medium

def generate_audio(prompt):
  music_pipe = pipeline("text-to-audio", model="facebook/musicgen-small")
    #controls the length of the the song
  forward_params = {"max_new_tokens": 512}

  output = self.music_pipe(prompt, forward_params=forward_params)

  audio_data = np.array(output["audio"][0])
  sampling_rate = output["sampling_rate"]

  # Create an AudioSegment object
  audio_segment = AudioSegment(
      audio_data.tobytes(),
      frame_rate=sampling_rate,
      sample_width=audio_data.dtype.itemsize,
      channels=1  # Assuming mono audio
  )

  # Save the audio to an MP3 file
  audio_segment.export(prompt + ".mp3", format="mp3")

  Audio(output["audio"][0], rate=output["sampling_rate"])

  print("Saved audio as:", prompt, ".mp3")

def add_audio(audio_name, audio_path, start_frame=1, volume=0.5):
  """
  Imports given audio to blender
  
  Args:
      audio_name (string): name given to the audio, shown in blender
      audio_path (string): the local path to the imported audio
      start_frame (int): the frame to start the audio on
      volume (float): a float between 0-1 representing volume
  """
  scene = bpy.context.scene
  audio_strip = scene.sequence_editor.sequences.new_sound(name=audio_name, filepath=audio_path, channel=1, frame_start=start_frame)
  audio_strip.volume = volume
