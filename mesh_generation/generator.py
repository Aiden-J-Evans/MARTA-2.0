#################
#
# Author: Aiden
# Currently not in use, as it requires a newer version of torch
#
#################
import torch
import os
from meshgpt_pytorch import (
    MeshAutoencoder,
    MeshTransformer,
    mesh_render
)

def generate_object(prompt : str) -> str:
    """
    !!! Currently not working, needs a newer version of torch incompatible with other parts of the project !!!\n

    Generates an object from the given prompt

    Args:
        prompt (str): the object to be generated

    Returns:
        (str) the path to the object
    """
    # Code taken from https://huggingface.co/MarcusLoren/MeshGPT-preview
    device = "cuda" if torch.cuda.is_available() else "cpu"
    transformer = MeshTransformer.from_pretrained("MarcusLoren/MeshGPT-preview").to(device)

    output = []
    output.append((transformer.generate(texts = [prompt]))) 
    
    path = os.getcwd() + '\\mesh_generation\\generated_objects\\' + prompt + '.obj'

    mesh_render.save_rendering(path, output)
    
    return path
