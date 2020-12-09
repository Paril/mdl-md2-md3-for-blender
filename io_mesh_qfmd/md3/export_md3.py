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

from ..quakenorm import encode_md3_normal
from .md3 import *

def make_shader(operator, surface, mesh):
    materials = bpy.context.object.data.materials

    if not len(materials):
        return

    for mat in materials:
        allTextureNodes = list(filter(lambda node: node.type == "TEX_IMAGE", mat.node_tree.nodes))
        if len(allTextureNodes) != 1:
            continue
        node = allTextureNodes[0]
        if node.type == "TEX_IMAGE":
            image = node.image
            skin = image.name
            surface.shaders.append(MD3Shader(skin))

def build_tris(mesh, surface: MD3Surface):
    vertlist = []

    for face in mesh.polygons:
        ntri = MD3Triangle([ 0, 0, 0 ])
        l_i = face.loop_indices
        for v,vert_index in enumerate(face.vertices):
            uv_map = mesh.uv_layers.active.data[l_i[v]].uv ## UNWRAP ## see log for details ##
            uv = (uv_map.x, 1.0 - uv_map.y)
            match = 0
            match_index = 0
            for i,vi in enumerate(vertlist):
                if vi == vert_index:
                    if surface.texcoords[i].st == uv:
                        match = 1
                        match_index = i
            if match == 0:
                ntri.v[v] = len(vertlist) ## TRIANGULATE ## see log for details ##
                ntex = MD3TexCoord(uv)
                surface.texcoords.append(ntex)
                vertlist.append(vert_index)
            else:
                ntri.v[v] = match_index
        ntri.v = (ntri.v[0], ntri.v[2], ntri.v[1])
        surface.triangles.append(ntri)

    return vertlist

def make_surface(surface, mesh, vertlist):
    for vi in vertlist:
        mv = mesh.vertices[vi]
        surface.verts.append(MD3Vertex(tuple(mv.co), encode_md3_normal(mv.normal)))

def name_frame(frame_number):
    if bpy.context.object.data.shape_keys:
        shape_keys_amount = len(bpy.context.object.data.shape_keys.key_blocks)
        if shape_keys_amount > frame_number:
            return bpy.context.object.data.shape_keys.key_blocks[frame_number].name

    return "frame" + str(frame_number)

def export_md3(
    operator,
    context,
    filepath = "",
    xform = True
    ):

    print("Start MD3 Export...\n")

    objects = context.selected_objects
    mdl = MD3(filepath)

    # set up surfaces
    for obj in objects:
        print("Surface name: " + str(obj.name))
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        context.scene.frame_set(context.scene.frame_start)
        obj.update_from_editmode()
        depsgraph = context.evaluated_depsgraph_get()
        ob_eval = obj.evaluated_get(depsgraph)
        mesh = ob_eval.to_mesh()

        surf = MD3Surface(obj.name)
        surf.obj = obj

        # set up shader, tris and texcoords
        make_shader(operator, surf, mesh)
        vertlist = build_tris(mesh, surf)
        ob_eval.to_mesh_clear()

        # build verts
        for fno in range(context.scene.frame_start, context.scene.frame_end + 1):
            context.scene.frame_set(fno)
            obj.update_from_editmode()
            depsgraph = context.evaluated_depsgraph_get()
            ob_eval = obj.evaluated_get(depsgraph)
            mesh = ob_eval.to_mesh()
            if xform:
                mesh.transform(obj.matrix_world)
                mesh.calc_normals_split()
            make_surface(surf, mesh, vertlist)
            ob_eval.to_mesh_clear()

        mdl.surfaces.append(surf)

    # set up frames, since we need the bounds first anyways
    for fno in range(context.scene.frame_start, context.scene.frame_end + 1):
        mdl.frames.append(MD3Frame(name_frame(fno)))

    # scale verts
    for surf in mdl.surfaces:
        for vert in surf.verts:
            vert.xyz = tuple(map(lambda x: int(x * MD3Vertex.Scale), vert.xyz))

    mdl.write(filepath)
    return {'FINISHED'}
