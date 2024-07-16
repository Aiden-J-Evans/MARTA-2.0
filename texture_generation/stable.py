###########################################################################
# Code taken from https://huggingface.co/stabilityai/stable-diffusion-2-1 #
###########################################################################

import torch, os
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

model_id = "stabilityai/stable-diffusion-2-1"

# Use the DPMSolverMultistepScheduler (DPM-Solver++) scheduler here instead
pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
pipe = pipe.to("cuda")

def generate_image(prompt):
    """
    Generates an image using stable-diffusion 2.1 based off a prompt

    Args:
        prompt (str): the prompt the model uses to generate the image

    Returns:
        The path to the saved image (png)
    """
    image = pipe(prompt).images[0]
    path = os.getcwd() + "//texture_generation//generated_images//" + prompt + ".png"
    image.save(path)
    return path