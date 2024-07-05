import torch
import os
from meshgpt_pytorch import (
    MeshAutoencoder,
    MeshTransformer,
    mesh_render
)

def generate_object(prompt):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    transformer = MeshTransformer.from_pretrained("MarcusLoren/MeshGPT-preview").to(device)

    output = []
    output.append((transformer.generate(texts = [prompt]))) 
    
    path = os.getcwd() + '\\mesh_generation\\generated_objects\\' + prompt + '.obj'

    mesh_render.save_rendering(path, output)
    
    return path

generate_object('human')