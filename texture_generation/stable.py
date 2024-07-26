###########################################################################
# Code taken from https://huggingface.co/stabilityai/stable-diffusion-2-1 #
###########################################################################

import torch, os, gc
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler

def generate_image(prompt, path, height = 512, width = 512):
    """
    Generates an image using stable-diffusion 2.1 based off a prompt

    Args:
        prompt (str): the prompt the model uses to generate the image

    Returns:
        The path to the saved image (png)
    """
    pipe = StableDiffusionPipeline.from_pretrained('stabilityai/stable-diffusion-2-1', torch_dtype=torch.float16)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("cuda")
    pipe.enable_attention_slicing() 
    pipe.enable_model_cpu_offload()
    torch.cuda.empty_cache()
    image = pipe(prompt, height=height, width=width).images[0]
    image.save(path)
    torch.cuda.empty_cache()
    gc.collect()
    return path
