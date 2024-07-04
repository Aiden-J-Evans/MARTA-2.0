import subprocess
import os

def initialize(): 
    """Initializes the environment and modules needed to run MARTA-2.0"""
    result = subprocess.run(['conda', 'env', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False, shell=True)
    
    # Check if the specified environment name is in the list of environments
    if 'momask' not in str(result.stdout):
        print('Creating momask conda environment...')
        subprocess.run(["cd momask-codes"])
        subprocess.run(["conda", "create", "-n", "momask", "python=3.8"], shell=True)
        subprocess.run(["conda", "activate", "momask"], shell=True)
        subprocess.run(["conda", "install", "pytorch", "torchvision", "torchaudio", "pytorch-cuda=11.8", "-c", "pytorch", "-c nvidia"], shell=True)
        subprocess.call(["pip", "install", "-r", "requirements.txt"])
        subprocess.call(["conda", "install", "spacy"], shell=True)
        subprocess.call(["conda", "install", "transformers"], shell=True)
        #subprocess.call(["conda", "install", "-c", "conda-forge", "ffmpeg=4.3.0"], shell=True)
        subprocess.call(['cd..'])
    elif 'momask' in str(result.stdout) and not os.getenv('CONDA_PREFIX'):
        print("activating environment...")
        subprocess.run(["conda", "activate", "momask"], shell=True)
        print('done')
    else:
        print("env already created and activated")

    if not os.path.exists("momask-codes\\checkpoints"):
        print('done... ensure that you have created "checkpoints" directory with two subdirectories "kit" and "t2m", with their respective zip files inside from https://drive.google.com/file/d/1MNMdUdn5QoO8UW1iwTcZ0QNaLSH4A6G9/view and https://drive.google.com/file/d/1dtKP2xBk-UjG9o16MVfBJDmGNSI56Dch/view')
        
def create_animation(prompt, length):
    """Genreates an animation from a given prompt and length
    
    Args:
        prompt (str): The prompt for the animation
        length (int): The length of the animation in seconds

    Returns:
        (str) The working directory path to the generated animation

    """
    os.chdir("momask-codes")
    subprocess.call(["python", "gen_t2m.py", "--gpu_id", "0", "--ext", prompt, "--text_prompt", "\""+ prompt +"\"", "--motion_length", str(length*20)], shell=True)
    os.chdir("..")
    return "momask-codes\\generation\\" + prompt + "\\0\\sample0_repeat0_length" + str(length*20) + ".bvh"
    
