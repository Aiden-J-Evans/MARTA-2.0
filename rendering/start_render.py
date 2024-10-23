import subprocess, os

BLENDER_SCRIPT = 'rendering/renderer.py'

def render(frame_data_path):
    """Activates the rendering script in blender"""
    subprocess.call(["blender", "-P", BLENDER_SCRIPT, "--", frame_data_path])

if __name__ == "__main__":
    story_name = input("What is the name of the story you want to render? ")
    render(os.path.join(os.getcwd(), "output", story_name, story_name.replace(" ", "_") + "_frame_data.json"))

