import bpy

# Import the character
fbx_file_path = r"C:\Users\PMLS\Documents\makehuman\v1py3\exports\t pose soldier.fbx"
bpy.ops.import_scene.fbx(filepath=fbx_file_path, use_manual_orientation=True, use_anim=False, axis_forward='-Y', axis_up='Z')

# Import the animation
animation_path = r'C:\Users\PMLS\Desktop\blender stuff\animations\momask animation.bvh'
bpy.ops.import_anim.bvh(filepath=animation_path, axis_forward='Z', axis_up='Y')

# Retargeting function
def retarget_rokoko(source_armature, target_armature):
    def enable_addon(addon_name):
        if addon_name not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=addon_name)

    # Enable the Rokoko Addon
    enable_addon('rokoko-studio-live-blender')

    # Function to build bone list
    def build_bone_list():
        if source_armature:
            bpy.context.scene.rsl_retargeting_armature_source = source_armature
        else:
            print("Source Armature not found")
        if target_armature:
            bpy.context.scene.rsl_retargeting_armature_target = target_armature
        else:
            print("Target Armature not found")
        bpy.ops.rsl.build_bone_list()
    
    build_bone_list()

    # Function to retarget using the Rokoko addon
    def retarget_animation():
        bpy.ops.rsl.retarget_animation()
    
    retarget_animation()

# Function to apply animation to all armatures in a collection
def apply_animation_to_armatures(source_armature_name, collection_name):
    source_armature = bpy.data.objects.get(source_armature_name)
    if not source_armature:
        print(f"Source Armature '{source_armature_name}' not found")
        return
    
    collection = bpy.data.collections.get(collection_name)
    if not collection:
        print(f"Collection '{collection_name}' not found")
        return
    
    for target_armature in collection.objects:
        if target_armature.type == 'ARMATURE':
            print(f"Retargeting animation to '{target_armature.name}'")
            retarget_rokoko(source_armature, target_armature)

# Example usage
apply_animation_to_armatures('SourceArmature', 'ArmatureCollection')
