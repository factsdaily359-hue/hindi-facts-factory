import bpy
import json
import math
import os
import sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
meta_path, out_dir = args[0], args[1]
mode = args[2] if len(args) > 2 else "short"
is_long = mode == "long"
render_width, render_height = (960, 540) if is_long else (540, 960)
scene_limit = 8 if is_long else 5
with open(meta_path, "r", encoding="utf-8") as f:
    data = json.load(f)
os.makedirs(out_dir, exist_ok=True)

def mat(name, color, metallic=0.0, roughness=0.35, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    if emission:
        p.inputs["Emission Color"].default_value = (*color, 1)
        p.inputs["Emission Strength"].default_value = emission
    return m

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass

def add_uv(name, loc, scale, material, segments=48, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale if isinstance(scale, tuple) else (scale, scale, scale)
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o

def add_torus(name, loc, major, minor, material, rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=96, minor_segments=12, location=loc, rotation=rot)
    o=bpy.context.object; o.name=name; o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o

def setup_camera():
    bpy.ops.object.camera_add(location=(0,-10,2.4))
    cam=bpy.context.object
    cam.data.lens=48
    bpy.context.scene.camera=cam
    target=Vector((0,0,0))
    direction=target-cam.location
    cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    cam.keyframe_insert(data_path="location", frame=1)
    cam.location=(0.8,-8.6,2.0)
    cam.keyframe_insert(data_path="location", frame=96)
    cam.location=(-0.5,-8.1,2.8)
    cam.keyframe_insert(data_path="location", frame=192)
    return cam

def light_setup():
    bpy.ops.object.light_add(type="AREA", location=(2,-5,6))
    key=bpy.context.object; key.data.energy=1500; key.data.shape="DISK"; key.data.size=5
    bpy.ops.object.light_add(type="AREA", location=(-5,1,2))
    fill=bpy.context.object; fill.data.energy=900; fill.data.color=(0.18,0.45,1.0); fill.data.size=4
    bpy.ops.object.light_add(type="POINT", location=(3,3,3))
    rim=bpy.context.object; rim.data.energy=500; rim.data.color=(1.0,0.35,0.12)

def render_scene(index, label):
    clear_scene()
    scene=bpy.context.scene
    scene.render.engine="BLENDER_EEVEE_NEXT"
    scene.eevee.taa_render_samples=16
    scene.render.resolution_x=render_width
    scene.render.resolution_y=render_height
    scene.render.resolution_percentage=100
    scene.render.fps=24
    scene.render.image_settings.file_format="PNG"
    scene.world.color=(0.012,0.018,0.04)
    scene.view_settings.view_transform="AgX"
    dark=mat("Midnight", (0.012,0.025,0.06), roughness=0.8)
    blue=mat("Ocean Blue", (0.025,0.28,0.55), metallic=0.35)
    gold=mat("Warm Gold", (0.95,0.48,0.08), metallic=0.55)
    cyan=mat("Electric Cyan", (0.04,0.72,0.85), metallic=0.35, emission=0.25)
    green=mat("Nature Green", (0.08,0.42,0.18), roughness=0.5)
    white=mat("Cloud White", (0.72,0.83,0.95), roughness=0.3)
    lower=label.lower()
    # A real 3D environment, with a topic-relevant hero object and animated orbiting details.
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-2.1))
    floor=bpy.context.object; floor.data.materials.append(dark)
    if any(k in lower for k in ("अंतरिक्ष","ग्रह","सूर्य","चंद्र","तारा","पृथ्वी","space","planet","moon")):
        hero=add_uv("Planet",(0,0,0),(1.65,1.65,1.65),blue)
        add_torus("Orbital ring",(0,0,0),2.25,0.045,gold,(math.radians(68),0,math.radians(18)))
        add_uv("Moon",(2.8,0.4,0.8),0.34,white)
        hero.rotation_euler=(0,0,0)
    elif any(k in lower for k in ("समुद्र","पानी","महासागर","मछली","व्हेल","ocean","sea","fish")):
        hero=add_uv("Ocean sphere",(0,0,0),(1.8,1.1,1.2),blue)
        for j in range(4):
            fish=add_uv("Swimming fish "+str(j),(-2.8+j*1.5,0.0,0.45*math.sin(j)),(0.35,0.16,0.14),gold if j%2==0 else cyan)
            fish.keyframe_insert(data_path="location",frame=1)
            fish.location.x += 1.4
            fish.keyframe_insert(data_path="location",frame=96)
    elif any(k in lower for k in ("पेड़","जंगल","पौधा","पत्ता","फूल","प्रकृति","वन","tree","forest","plant")):
        for j in range(5):
            x=-2.4+j*1.2
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.13, depth=1.8, location=(x,0,-0.6))
            trunk=bpy.context.object; trunk.data.materials.append(gold)
            add_uv("Tree canopy",(x,0,0.65),0.75,green)
        hero=add_uv("Glowing sun",(1.7,0.8,1.4),0.42,gold)
    elif any(k in lower for k in ("जानवर","हाथी","शेर","पक्षी","कुत्ता","बिल्ली","चींटी","साँप","animal","bird")):
        body=add_uv("Animal body",(0,0,0),(1.5,0.72,0.8),gold)
        head=add_uv("Animal head",(1.2,-0.05,0.45),0.58,gold)
        for x in (-0.8,0.8):
            for y in (-0.42,0.42):
                leg=add_uv("Moving leg",(x,y,-0.9),(0.18,0.2,0.62),gold)
                leg.rotation_euler.y=0.15
                leg.keyframe_insert(data_path="rotation_euler",frame=1)
                leg.rotation_euler.y=-0.25
                leg.keyframe_insert(data_path="rotation_euler",frame=48)
                leg.rotation_euler.y=0.15
                leg.keyframe_insert(data_path="rotation_euler",frame=96)
        hero=head
    elif any(k in lower for k in ("कंप्यूटर","मोबाइल","इंटरनेट","रोबोट","चिप","तकनीक","बिजली","computer","technology","robot")):
        bpy.ops.mesh.primitive_cube_add(size=1.8, location=(0,0,0))
        hero=bpy.context.object; hero.name="Technology core"; hero.data.materials.append(blue)
        bevel=hero.modifiers.new("Rounded edges","BEVEL"); bevel.width=0.18; bevel.segments=5
        hero.modifiers.new("Weighted normals","WEIGHTED_NORMAL")
        for j in range(3):
            add_torus("Signal ring",(0,0,0),1.5+j*0.35,0.025,cyan,(math.radians(90),0,0))
    else:
        hero=add_uv("Discovery core",(0,0,0),1.45,gold)
        for j in range(3):
            add_torus("Discovery orbit",(0,0,0),2.0+j*0.35,0.025,cyan,(math.radians(35+j*35),math.radians(j*25),0))
    # Floating particles add depth; each drifts on a different path.
    for j in range(18):
        x=-3.4+(j%6)*1.35
        z=-1.1+(j//6)*1.15
        p=add_uv("Floating particle "+str(j),(x,0.9,z),0.045+(j%3)*0.018,cyan if j%2 else gold,24,12)
        p.keyframe_insert(data_path="location",frame=1)
        p.location.z += 0.35+0.08*(j%4)
        p.location.x += 0.25*((j%3)-1)
        p.keyframe_insert(data_path="location",frame=96)
    if "hero" in locals() and hero:
        hero.rotation_euler=(0,0,0)
        hero.keyframe_insert(data_path="rotation_euler",frame=1)
        hero.rotation_euler=(0.18,0.35,math.radians(90))
        hero.keyframe_insert(data_path="rotation_euler",frame=96)
    setup_camera(); light_setup()
    # Smooth interpolation for cinematic camera/object motion.
    for obj in scene.objects:
        if obj.animation_data and obj.animation_data.action:
            for fc in obj.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation="BEZIER"
    scene.frame_start=1; scene.frame_end=72 if is_long else 96
    scene.render.image_settings.file_format="PNG"
    scene.render.filepath=os.path.join(out_dir, "3d_frame_")
    # Render frames, then encode this scene as an MP4.
    bpy.ops.render.render(animation=True)
    scene_dir=os.path.join(out_dir,"blender_frames_"+str(index))
    os.makedirs(scene_dir,exist_ok=True)
    for name in os.listdir(out_dir):
        if name.startswith("3d_frame_") and name.endswith(".png"):
            os.replace(os.path.join(out_dir,name),os.path.join(scene_dir,name))
    import subprocess
    clip=os.path.join(out_dir,"3d_scene_"+str(index)+".mp4")
    subprocess.run(["ffmpeg","-y","-framerate","24","-i",os.path.join(scene_dir,"3d_frame_%04d.png"),
                    "-c:v","libx264","-preset","veryfast","-crf","24","-pix_fmt","yuv420p",clip],check=True)
    return clip

clips=[]
for i, label in enumerate((data.get("scenes",[]) if is_long else data.get("screens",[]))[:scene_limit],1):
    clips.append(render_scene(i,label))
concat=os.path.join(out_dir,"3d_scenes.txt")
with open(concat,"w",encoding="utf-8") as f:
    for clip in clips:
        f.write("file '"+clip.replace("'","'\\''")+"'\n")
visual=os.path.join(out_dir,"long_3d_visuals.mp4" if is_long else "three_d_visuals.mp4")
import subprocess
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",concat,"-c","copy",visual],check=True)
print("3D_RENDER_COMPLETE",visual)
