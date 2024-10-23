import subprocess, os, torch, gc

def create_animation(prompt, length = 5, story_name=str):
    """Genreates an animation from a given prompt and length\n
    !!! Automatically naviages to the momask-codes directory !!!\n
    Args:
        prompt (str): The prompt for the animation
        length (int): The length of the animation in seconds

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

def create_idle(length = 5, index = 0, story_name = str):
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

if __name__ == "__main__":
    create_animation("A man dances", story_name="Aiden and Musfira")

