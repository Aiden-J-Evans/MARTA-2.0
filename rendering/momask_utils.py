import subprocess
import os

def initialize(): 
    result = subprocess.run(['conda', 'env', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False)
    
    # Check if the specified environment name is in the list of environments
    if 'momask' not in str(result.stdout):
        print('Creating momask conda environment')
        subprocess.run(["conda", "create", "-n", "momask", "python=3.8"])
        subprocess.run(["conda", "activate", "momask"])
        subprocess.run(["conda", "install", "pytorch", "torchvision", "torchaudio", "pytorch-cuda=11.8", "-c", "pytorch", "-c nvidia"])
        subprocess.call(["conda", "install", "spacy"])
        subprocess.call(["conda", "install", "transformers"])
        subprocess.call(["conda", "install", "-c", "conda-forge", "ffmpeg=4.3.0"])
    elif 'momask' in str(result.stdout) and not os.getenv('CONDA_PREFIX'):
        print("activating environment")
        subprocess.run(["conda", "activate", "momask"])
    else:
        print("env already created an activated")


def create_animation(prompt):
    os.chdir("momask-codes")
    subprocess.call(["python", "gen_t2m.py", "--gpu_id", "0", "--ext", "exp1", "--text_prompt", "\""+ prompt +"\""])
    os.chdir("..")
    
create_animation("A person skipping forward.")