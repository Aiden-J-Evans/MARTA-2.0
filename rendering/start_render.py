import subprocess

BLENDER_SCRIPT = 'rendering/renderer.py'

def render(scene_file, out_file):
    subprocess.call(["blender", "-b", "--python", BLENDER_SCRIPT, "--", scene_file, out_file])
    
if __name__ == "__main__":
    SCENE_FILE = 'main.scene'
    OUTPUT_FILE = 'output/out.mp4'

    render(SCENE_FILE, OUTPUT_FILE)
    print("Done")