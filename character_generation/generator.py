import torch
from meshgpt_pytorch import (
    MeshAutoencoder,
    MeshTransformer,
    mesh_render
)

device = "cuda" if torch.cuda.is_available() else "cpu"
transformer = MeshTransformer.from_pretrained("MarcusLoren/MeshGPT-preview").to(device)

output = []
output.append((transformer.generate(texts = ['rock']))) 

mesh_render.save_rendering(f'./render.obj', output)

