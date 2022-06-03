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

from ..quakenorm import map_normal
from .md2 import MD2

def check_faces(mesh):
    #Check that all faces are tris because mdl does not support anything else.
    #Because the diagonal on which a quad is split can make a big difference,
    #quad to tri conversion will not be done automatically.
    faces_ok = True
    save_select = []
    for f in mesh.polygons:
        save_select.append(f.select)
        f.select = False
        if len(f.vertices) > 3:
            f.select = True
            faces_ok = False
    if not faces_ok:
        mesh.update()
        return False
    #reset selection to what it was before the check.
    for f, s in map(lambda x, y: (x, y), mesh.polygons, save_select):
        f.select = s
    mesh.update()
    return True

def make_skin(operator, mdl, mesh):
    mdl.skinwidth, mdl.skinheight = (4, 4)

    materials = bpy.context.object.data.materials

    if not len(materials):
        return

    for mat in materials:
        if not mat.use_nodes:
            continue
        allTextureNodes = list(filter(lambda node: node.type == "TEX_IMAGE", mat.node_tree.nodes))
        if len(allTextureNodes) != 1:
            continue
        node = allTextureNodes[0]
        if node.type == "TEX_IMAGE":
            image = node.image
            mdl.skinwidth, mdl.skinheight = image.size
            skin = image.name
            mdl.skins.append(MD2.Skin(skin))

def build_tris(meshes):
    stverts = []
    tris = []
    vuvdict = {}
    vert_offset = 0

    for m in range(len(meshes)):
        uvfaces = meshes[m].uv_layers.active.data
        for face in meshes[m].polygons:
            fv = list(face.vertices)
            uv = uvfaces[face.loop_start:face.loop_start + face.loop_total]
            uv = list(map(lambda a: a.uv, uv))
            for i in range(1, len(fv) - 1):
                uvs = [tuple(uv[0]), tuple(uv[i + 1]), tuple(uv[i])]

                for st in uvs:
                    if st not in vuvdict:
                        vuvdict[st] = len(stverts)
                        stverts.append(MD2.STVert(st))

                # blender's and quake's vertex order are opposed
                tris.append(MD2.Tri((fv[0] + vert_offset, fv[i + 1] + vert_offset, fv[i] + vert_offset), (vuvdict[uvs[0]], vuvdict[uvs[1]], vuvdict[uvs[2]])))
        vert_offset = vert_offset + len(meshes[m].vertices)
        print(vert_offset)
    return tris, stverts

def convert_stverts(mdl, stverts):
    for i, st in enumerate(stverts):
        # quake textures are top to bottom, but blender images
        # are bottom to top
        st.s = int(st.s * (mdl.skinwidth - 1))
        st.t = int((1 - st.t) * (mdl.skinheight - 1))
        # ensure st is within the skin
        if (mdl.skinwidth and mdl.skinheight):
          st.s = ((st.s % mdl.skinwidth) + mdl.skinwidth) % mdl.skinwidth
          st.t = ((st.t % mdl.skinheight) + mdl.skinheight) % mdl.skinheight
        else:
          st.s = st.t = 0

def make_frame(frame, mesh):
    for mv in mesh.vertices:
        vert = MD2.Vert(tuple(mv.co), map_normal(mv.normal))
        frame.add_vert(vert)

def name_frame(frame_number):
    if bpy.context.object.data.shape_keys:
        shape_keys_amount = len(bpy.context.object.data.shape_keys.key_blocks)
        if shape_keys_amount > frame_number:
            return bpy.context.object.data.shape_keys.key_blocks[frame_number].name
        else:
            return "frame" + str(frame_number)
    else:
        return "frame" + str(frame_number)

def export_md2(
    operator,
    context,
    filepath = "",
    xform = True
    ):

    print("Start MD2 Export...\n")

    meshes = []
    objects = context.selected_objects
    for i in range(len(objects)):
        print("Object name: " + str(objects[i].name))
        bpy.ops.object.select_all(action='DESELECT')
        objects[i].select_set(True)
        context.view_layer.objects.active = objects[i]
        objects[i].update_from_editmode()
        depsgraph = context.evaluated_depsgraph_get()
        ob_eval = objects[i].evaluated_get(depsgraph)
        mesh = ob_eval.to_mesh()
        meshes.append(mesh)
        if i == 0:
            mdl = MD2(objects[0].name)
            mdl.obj = objects[0]
            make_skin(operator, mdl, mesh)
    mdl.tris, mdl.stverts = build_tris(meshes)

    if not mdl.frames:
        for fno in range(context.scene.frame_start, context.scene.frame_end + 1):
            context.scene.frame_set(fno)
            frame = MD2.Frame()
            frame.name = name_frame(fno)
            for i in range(len(objects)):
                objects[i].update_from_editmode()
                depsgraph = context.evaluated_depsgraph_get()
                ob_eval = objects[i].evaluated_get(depsgraph)
                mesh = ob_eval.to_mesh()
                if xform:
                    mesh.transform(mdl.obj.matrix_world)
                    mesh.calc_normals_split()
                make_frame(frame, mesh)
            frame.calc_scale()
            frame.scale_verts()
            mdl.frames.append(frame)

    convert_stverts(mdl, mdl.stverts)
    mdl.write(filepath)
    return {'FINISHED'}
