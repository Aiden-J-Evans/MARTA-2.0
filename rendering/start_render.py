import subprocess

BLENDER_SCRIPT = 'rendering/renderer.py'

def render():
    subprocess.call(["blender", "-P", BLENDER_SCRIPT])
