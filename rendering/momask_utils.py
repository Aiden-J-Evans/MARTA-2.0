"""
Author: Aiden
NOTE:
- create_animation() automatically navigates throught cmd
- MoMask has specific quirks. Read comments for more info
"""

import subprocess, os, torch, gc

def create_animation(prompt : str, length: int, story_name: str) -> str:
    """Genreates an animation from a given prompt and length\n
    !!! Automatically naviages to the momask-codes directory !!!\n
    Args:
        prompt (str): The prompt for the animation
        length (int): The length of the animation in seconds
        story_name (str): the name of the story for organizational purposes
    Returns:
        (str) The new path to the generated animation
    """
    print("Generating animation...")

    length *= 32
    os.chdir("momask-codes")
    subprocess.call(["python", "gen_t2m.py", "--gpu_id", "0", "--ext", prompt, "--text_prompt", "\""+ prompt +"\"", "--motion_length", str(length)], shell=True)
    os.chdir("..")

    og_path = os.path.join(os.getcwd(), "momask-codes", "generation", prompt, "animations", "0", "sample0_repeat0_len" + str(length) + ".mp4") 
    new_path = new_path = os.path.join(os.getcwd(), "rendering", "animations", story_name, prompt + ".mp4") 
    os.replace(og_path, new_path)
    
    og_path = os.path.join(os.getcwd(), "momask-codes", "generation", prompt, "animations", "0", "sample0_repeat0_len" + str(length) + ".bvh") 
    new_path = os.path.join(os.getcwd(), "rendering", "animations", story_name, prompt + ".bvh") 
    os.replace(og_path, new_path)

    torch.cuda.empty_cache()
    gc.collect()
    return new_path

def create_idle(length: int, index : int, story_name : str) -> str:
    """Genreates an idle animatoin animation from a given length\n
    !!! Automatically naviages to the momask-codes directory !!!\n
    Args:
        length (int): The length of the animation in seconds
        index (int): The index of this animation (so it doesnt do multiple times)
        story_name (str): The index of this animation (so it doesnt do multiple times)

    Returns:
        (str) The new path to the generated animation
    """
    print("Generating animation...")
    prompt = "a person standing still"

    # The length has to be a multiple of 4, for some reason
    length *= 32
    os.chdir("momask-codes")
    subprocess.call(["python", "gen_t2m.py", "--gpu_id", "0", "--ext", prompt, "--text_prompt", "\""+ prompt +"\"", "--motion_length", str(length)], shell=True)
    os.chdir("..")

    og_path = os.path.join(os.getcwd(), "momask-codes", "generation", prompt, "animations", "0", "sample0_repeat0_len" + str(length) + ".mp4") 
    new_path = new_path = os.path.join(os.getcwd(), "rendering", "animations", story_name, prompt + str(index) + ".mp4") 
    os.replace(og_path, new_path)
    
    og_path = os.path.join(os.getcwd(), "momask-codes", "generation", prompt, "animations", "0", "sample0_repeat0_len" + str(length) + ".bvh") 
    new_path = os.path.join(os.getcwd(), "rendering", "animations", story_name, prompt + str(index) + ".bvh") 
    os.replace(og_path, new_path)

    torch.cuda.empty_cache()
    gc.collect()
    return new_path


