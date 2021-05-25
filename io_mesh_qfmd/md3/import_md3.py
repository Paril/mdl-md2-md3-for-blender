# vim:ts=4:et
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import bpy
from mathutils import Vector,Matrix

from .md3 import MD3, MD3Frame, MD3Shader, MD3Surface, MD3TexCoord, MD3Triangle, MD3Vertex

def make_verts(mdl: MD3, surf: MD3Surface, framenum: int):
    num_verts = len(surf.verts) // len(mdl.frames)
    verts_start = framenum * num_verts
    verts_end = verts_start + num_verts
    verts = []
    for i in range(verts_start, verts_end):
        verts.append(list(map(lambda x: x / MD3Vertex.Scale, surf.verts[i].xyz)))
    return verts

def make_faces(surf: MD3Surface):
    faces = []
    uvs = []
    tri: MD3Triangle
    for tri in surf.triangles:
        tv = list(tri.v)
        sts = [ list(surf.texcoords[tv[0]].st), list(surf.texcoords[tv[1]].st), list(surf.texcoords[tv[2]].st) ]
        for st in sts:
            # quake textures are top to bottom, but blender images
            # are bottom to top
            st[1] = 1 - st[1]
        # blender's and quake's vertex order seem to be opposed
        tv.reverse()
        sts.reverse()
        # annoyingly, blender can't have 0 in the final vertex, so rotate the
        # face vertices and uvs
        if not tv[2]:
            tv = [tv[2]] + tv[:2]
            sts = [sts[2]] + sts[:2]
        faces.append(tv)
        uvs.append(sts)
    return faces, uvs

def load_skins(mdl: MD3, surf: MD3Surface):
    def load_skin(skin: MD3Shader):
        img = bpy.data.images.new(skin.name, 1, 1)
        surf.images.append(img)
        p = [0.0] * 1 * 1 * 4
        for j in range(1):
            for k in range(1):
                l = ((1 - 1 - j) * 1 + k) * 4
                p[l + 0] = 0
                p[l + 1] = 0
                p[l + 2] = 0
                p[l + 3] = 1.0
        img.pixels[:] = p[:]
        img.pack()
        img.use_fake_user = True

    surf.images=[]
    for i, skin in enumerate(surf.shaders):
        load_skin(skin)

def setup_main_material(mdl: MD3, surf: MD3Surface, skin: MD3Shader):
    mat = bpy.data.materials.new(skin.name)
    mat.blend_method = 'OPAQUE'
    mat.diffuse_color = (1, 1, 1, 1)
    mat.metallic = 1
    mat.roughness = 1
    mat.specular_intensity = 0
    mat.use_nodes = True
    return mat

def setup_skins(mdl: MD3, surf: MD3Surface, uvs):
    load_skins(mdl, surf)
    uvloop = surf.mesh.uv_layers.new(name = surf.name)
    for i in range(len(surf.mesh.polygons)):
        poly = surf.mesh.polygons[i]
        mdl_uv = uvs[i]
        for j,k in enumerate(poly.loop_indices):
            uvloop.data[k].uv = mdl_uv[j]

    #Load all skins
    for i, skin in enumerate(surf.shaders):
        mat = setup_main_material(mdl, surf, skin)

        # TODO: turn transform to True and position it properly in editor
        emissionNode = mat.node_tree.nodes.new("ShaderNodeEmission")
        shaderOut = mat.node_tree.nodes["Material Output"]
        mat.node_tree.nodes.remove(mat.node_tree.nodes["Principled BSDF"])

        tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")

        tex_node.image = surf.images[i]
        tex_node.interpolation = "Linear"

        emissionNode.location = (0, 0)
        shaderOut.location = (200, 0)
        tex_node.location = (-300, 0)

        mat.node_tree.links.new(tex_node.outputs[0], emissionNode.inputs[0])
        mat.node_tree.links.new(emissionNode.outputs[0], shaderOut.inputs[0])
        surf.mesh.materials.append(mat)

def make_shape_key(mdl: MD3, surf: MD3Surface, framenum):
    frame: MD3Frame = mdl.frames[framenum]
    surf.framekeys.append(surf.obj.shape_key_add(name=frame.name))
    surf.framekeys[framenum].value = 0.0
    surf.keys.append(surf.framekeys[framenum])
    num_verts = len(surf.verts) // len(mdl.frames)
    for i in range(num_verts):
        offset = (framenum * num_verts) + i
        surf.framekeys[framenum].data[i].co = list(map(lambda x: x / MD3Vertex.Scale, surf.verts[offset].xyz))

def build_shape_keys(mdl: MD3, surf: MD3Surface):
    surf.framekeys = []
    surf.keys = []
    surf.obj.shape_key_add(name="Basis",from_mix=False)
    surf.mesh.shape_keys.name = surf.name
    surf.obj.active_shape_key_index = 0
    bpy.context.scene.frame_end = 0
    for i, _ in enumerate(mdl.frames):
        make_shape_key(mdl, surf, i)
        bpy.context.scene.frame_end += 1

    bpy.context.scene.frame_start = 1

def set_keys(act, data):
    for d in data:
        key, co = d
        dp = """key_blocks["%s"].value""" % key.name
        fc = act.fcurves.new(data_path = dp)
        fc.keyframe_points.add(len(co))
        for i in range(len(co)):
            fc.keyframe_points[i].co = co[i]
            fc.keyframe_points[i].interpolation = 'LINEAR'

def build_actions(mdl: MD3, surf: MD3Surface):
    sk = surf.mesh.shape_keys
    ad = sk.animation_data_create()
    track = ad.nla_tracks.new()
    track.name = surf.name
    start_frame = 0
    for i, frame in enumerate(mdl.frames):
        act = bpy.data.actions.new(frame.name)
        data = []
        other_keys = surf.keys[:]

        data.append((surf.framekeys[i], [(1.0, 1.0)]))
        if surf.framekeys[i] in other_keys:
            del(other_keys[other_keys.index(surf.framekeys[i])])
        co = [(1.0, 0.0)]
        for k in other_keys:
            data.append((k, co))

        set_keys(act, data)
        track.strips.new(act.name, start_frame, act)
        start_frame += 1

def import_md3(operator, context, filepath):
    bpy.context.preferences.edit.use_global_undo = False

    for obj in bpy.context.scene.collection.objects:
        obj.select_set(False)

    mdl = MD3()
    if not mdl.read(filepath):
        operator.report({'ERROR'},
            "Unrecognized format: %s %d" % (mdl.ident, mdl.version))
        return {'CANCELLED'}

    for surf in mdl.surfaces:
        faces, uvs = make_faces(surf)
        verts = make_verts(mdl, surf, 0)
        surf.mesh = bpy.data.meshes.new(surf.name)
        surf.mesh.from_pydata(verts, [], faces)
        surf.obj = bpy.data.objects.new(surf.name, surf.mesh)

        bpy.context.scene.collection.objects.link(surf.obj)
        surf.obj.select_set(True)
        bpy.context.view_layer.objects.active = surf.obj
        setup_skins(mdl, surf, uvs)

        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = 1
        if len(mdl.frames) > 1:
            build_shape_keys(mdl, surf)
            build_actions(mdl, surf)

    surf.mesh.update()

    bpy.context.preferences.edit.use_global_undo = True
    return {'FINISHED'}