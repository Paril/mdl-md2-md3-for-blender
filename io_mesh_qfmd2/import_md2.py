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
from bpy_extras.object_utils import object_data_add
from mathutils import Vector,Matrix

from .md2 import MD2

def make_verts(mdl: MD2, framenum: int):
    frame: MD2.Frame = mdl.frames[framenum]
    verts = []
    s = Vector(frame.scale)
    o = Vector(frame.translate)
    m = Matrix(((s.x,  0,  0,o.x),
                (  0,s.y,  0,o.y),
                (  0,  0,s.z,o.z),
                (  0,  0,  0,  1)))
    for v in frame.verts:
        verts.append(m @ Vector(v.r))
    return verts

def make_faces(mdl: MD2):
    faces = []
    uvs = []
    for tri in mdl.tris:
        tv = list(tri.verts)
        sts = []
        for v in tri.tcs:
            stv = mdl.stverts[v]
            s = stv.s
            t = stv.t
            # quake textures are top to bottom, but blender images
            # are bottom to top
            sts.append((s / mdl.skinwidth, 1 - (t / mdl.skinheight)))
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

def load_skins(mdl: MD2):
    def load_skin(skin: MD2.Skin):
        img = bpy.data.images.new(skin.name, mdl.skinwidth, mdl.skinheight)
        mdl.images.append(img)
        p = [0.0] * mdl.skinwidth * mdl.skinheight * 4
        for j in range(mdl.skinheight):
            for k in range(mdl.skinwidth):
                l = ((mdl.skinheight - 1 - j) * mdl.skinwidth + k) * 4
                p[l + 0] = 0
                p[l + 1] = 0
                p[l + 2] = 0
                p[l + 3] = 1.0
        img.pixels[:] = p[:]
        img.pack()
        img.use_fake_user = True

    mdl.images=[]
    for i, skin in enumerate(mdl.skins):
        load_skin(skin)

def setup_main_material(mdl: MD2) -> 'Material':
    mat = bpy.data.materials.new(mdl.name)
    mat.blend_method = 'OPAQUE'
    mat.diffuse_color = (1, 1, 1, 1)
    mat.metallic = 1
    mat.roughness = 1
    mat.specular_intensity = 0
    mat.use_nodes = True
    return mat

def setup_skins(mdl: MD2, uvs):
    load_skins(mdl)
    uvloop = mdl.mesh.uv_layers.new(name = mdl.name)
    for i in range(len(mdl.mesh.polygons)):
        poly = mdl.mesh.polygons[i]
        mdl_uv = uvs[i]
        for j,k in enumerate(poly.loop_indices):
            uvloop.data[k].uv = mdl_uv[j]

    #Load all skins
    for i, skin in enumerate(mdl.skins):
        mat = setup_main_material(mdl)

        # TODO: turn transform to True and position it properly in editor
        emissionNode = mat.node_tree.nodes.new("ShaderNodeEmission")
        shaderOut = mat.node_tree.nodes["Material Output"]
        mat.node_tree.nodes.remove(mat.node_tree.nodes["Principled BSDF"])

        tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")

        tex_node.image = mdl.images[i]
        tex_node.interpolation = "Linear"

        emissionNode.location = (0, 0)
        shaderOut.location = (200, 0)
        tex_node.location = (-300, 0)

        mat.node_tree.links.new(tex_node.outputs[0], emissionNode.inputs[0])
        mat.node_tree.links.new(emissionNode.outputs[0], shaderOut.inputs[0])
        mdl.mesh.materials.append(mat)

def make_shape_key(mdl: MD2, framenum):
    frame: MD2.Frame = mdl.frames[framenum]
    frame.key = mdl.obj.shape_key_add(name=frame.name)
    frame.key.value = 0.0
    mdl.keys.append(frame.key)
    s = Vector(frame.scale)
    o = Vector(frame.translate)
    m = Matrix(((s.x,  0,  0,o.x),
                (  0,s.y,  0,o.y),
                (  0,  0,s.z,o.z),
                (  0,  0,  0,  1)))
    for i, v in enumerate(frame.verts):
        frame.key.data[i].co = m @ Vector(v.r)

def build_shape_keys(mdl):
    mdl.keys = []
    mdl.obj.shape_key_add(name="Basis",from_mix=False)
    mdl.mesh.shape_keys.name = mdl.name
    mdl.obj.active_shape_key_index = 0
    bpy.context.scene.frame_end = 0
    for i, frame in enumerate(mdl.frames):
        frame = mdl.frames[i]
        make_shape_key(mdl, i)
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

def build_actions(mdl):
    sk = mdl.mesh.shape_keys
    ad = sk.animation_data_create()
    track = ad.nla_tracks.new()
    track.name = mdl.name
    start_frame = 0
    for frame in mdl.frames:
        act = bpy.data.actions.new(frame.name)
        data = []
        other_keys = mdl.keys[:]

        data.append((frame.key, [(1.0, 1.0)]))
        if frame.key in other_keys:
            del(other_keys[other_keys.index(frame.key)])
        co = [(1.0, 0.0)]
        for k in other_keys:
            data.append((k, co))

        set_keys(act, data)
        track.strips.new(act.name, start_frame, act)
        start_frame += 1

def import_md2(operator, context, filepath, palette = 'PAL_QUAKE'):
    bpy.context.preferences.edit.use_global_undo = False

    for obj in bpy.context.scene.collection.objects:
        obj.select_set(False)

    mdl = MD2()
    if not mdl.read(filepath):
        operator.report({'ERROR'},
            "Unrecognized format: %s %d" % (mdl.ident, mdl.version))
        return {'CANCELLED'}
    faces, uvs = make_faces(mdl)
    verts = make_verts(mdl, 0)
    mdl.mesh = bpy.data.meshes.new(mdl.name)
    mdl.mesh.from_pydata(verts, [], faces)
    mdl.obj = bpy.data.objects.new(mdl.name, mdl.mesh)

    bpy.context.scene.collection.objects.link(mdl.obj)
    mdl.obj.select_set(True)
    bpy.context.view_layer.objects.active = mdl.obj
    setup_skins(mdl, uvs)

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = 1
    if len(mdl.frames) > 1:
        build_shape_keys(mdl)
        build_actions(mdl)

    mdl.mesh.update()

    bpy.context.preferences.edit.use_global_undo = True
    return {'FINISHED'}