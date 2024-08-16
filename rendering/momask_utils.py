import subprocess, os, torch, gc

def create_animation(prompt, length=5):
    """Genreates an animation from a given prompt and length\n
    !!! Automatically naviages to the momask-codes directory !!!\n
    Args:
        prompt (str): The prompt for the animation
        length (int): The length of the animation in seconds

    Returns:
        (str) The new path to the generated animation
    """
    print("Generating animation...")
    os.chdir("momask-codes")
    subprocess.call(["python", "gen_t2m.py", "--gpu_id", "0", "--ext", prompt, "--text_prompt", "\""+ prompt +"\"", "--motion_length", str(length*20)], shell=True)
    os.chdir("..")

    og_path = os.path.join(os.getcwd(), "momask-codes", "generation", prompt, "animations", "0", "sample0_repeat0_len" + str(length*20) + ".mp4") 
    new_path = new_path = os.path.join(os.getcwd(), "rendering", "animations", prompt + ".mp4") 
    os.replace(og_path, new_path)
    
    og_path = os.path.join(os.getcwd(), "momask-codes", "generation", prompt, "animations", "0", "sample0_repeat0_len" + str(length*20) + ".bvh") 
    new_path = os.path.join(os.getcwd(), "rendering", "animations", prompt + ".bvh") 
    os.replace(og_path, new_path)

   

    torch.cuda.empty_cache()
    gc.collect()
    return new_path

