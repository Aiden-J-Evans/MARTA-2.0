import subprocess
import os
        
def create_animation(prompt, length=5):
    """Genreates an animation from a given prompt and length
    
    Args:
        prompt (str): The prompt for the animation
        length (int): The length of the animation in seconds

    Returns:
        (str) The new path to the generated animation
    """
    subprocess.call(["python", "momask-codes/gen_t2m.py", "--gpu_id", "0", "--ext", prompt, "--text_prompt", "\""+ prompt +"\"", "--motion_length", str(length*20)], shell=True)
    og_path = os.getcwd() + "\\momask-codes\\generation\\" + prompt + "\\animations\\0\\sample0_repeat0_len" + str(length*20) + ".bvh"
    new_path = os.getcwd() + "\\rendering\\animations\\" + prompt + ".bvh"
    os.replace(og_path, new_path)
    return new_path
    