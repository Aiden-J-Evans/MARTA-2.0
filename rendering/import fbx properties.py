import bpy



fbx_file_path = r"C:\Users\PMLS\Documents\makehuman\v1py3\exports\t pose rigged goliath.fbx"


bpy.ops.import_scene.fbx(filepath=fbx_file_path, use_manual_orientation=True,  use_anim=False  , axis_forward='-Y', axis_up='Z')


animation_path=r'C:\Users\PMLS\Desktop\blender stuff\animations\momask animation.bvh'

bpy.ops.import_anim.bvh(
    filepath=animation_path,
    axis_forward='Z',
    axis_up='Y'
)
