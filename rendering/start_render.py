import subprocess

BLENDER_SCRIPT = 'rendering/renderer.py'

def render():
    subprocess.call(["blender", "-P", BLENDER_SCRIPT])

if __name__ == "__main__":
    render()