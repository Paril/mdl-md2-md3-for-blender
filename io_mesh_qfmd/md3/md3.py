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

from struct import unpack, pack
from mathutils import Vector

MaxPath = 64

class MD3Frame:
    MaxFrameName = 16
    Size = (12 * 3) + 4 + MaxFrameName

    def __init__(self, name=''):
        self.min_bounds = [ 0, 0, 0 ]
        self.max_bounds = [ 0, 0, 0 ]
        self.local_origin = [ 0, 0, 0 ]
        self.radius = 0
        self.name = name
    def read(self, mdl):
        self.min_bounds = mdl.read_float(3)
        self.max_bounds = mdl.read_float(3)
        self.local_origin = mdl.read_float(3)
        self.radius = mdl.read_float()
        self.name = mdl.read_path(MD3Frame.MaxFrameName)
        return self
    def write(self, mdl):
        mdl.write_float(self.min_bounds)
        mdl.write_float(self.max_bounds)
        mdl.write_float(self.local_origin)
        mdl.write_float(self.radius)
        mdl.write_path(self.name, MD3Frame.MaxFrameName)

class MD3Tag:
    Size = MaxPath + (4 * 3) + (4 * 9)

    def __init__(self, name=''):
        self.name = name
        self.origin = [ 0, 0, 0 ]
        self.axis = [ 1, 0, 0, 0, 1, 0, 0, 0, 1 ]
    def read(self, mdl):
        self.name = mdl.read_path(MaxPath)
        self.origin = mdl.read_float(3)
        self.axis = mdl.read_float(9)
        return self
    def write(self, mdl):
        mdl.write_path(self.name, MaxPath)
        mdl.write_float(self.origin)
        mdl.write_float(self.axis)

class MD3Shader:
    Size = MaxPath + 4

    def __init__(self, name='', index=0):
        self.name = name
        self.index = index
    def read(self, mdl):
        self.name = mdl.read_path(MaxPath)
        self.index = mdl.read_int()
        return self
    def write(self, mdl):
        mdl.write_path(self.name, MaxPath)
        mdl.write_int(self.index)

class MD3Triangle:
    Size = 4 * 3

    def __init__(self, v=None):
        self.v = ( 0, 0, 0 ) if not v else v
    def read(self, mdl):
        self.v = mdl.read_int(3)
        return self
    def write(self, mdl):
        mdl.write_int(self.v)

class MD3TexCoord:
    Size = 4 * 2

    def __init__(self, st=None):
        self.st = ( 0, 0 ) if not st else st
    def read(self, mdl):
        self.st = mdl.read_float(2)
        return self
    def write(self, mdl):
        mdl.write_float(self.st)

class MD3Vertex:
    Size = 2 * 4
    Scale = 64.0

    def __init__(self, xyz=None, normal=0):
        self.xyz = (0, 0, 0) if not xyz else xyz
        self.normal = normal
    def read(self, mdl):
        self.xyz = mdl.read_short(3)
        self.normal = mdl.read_ushort()
        return self
    def write(self, mdl):
        mdl.write_short(self.xyz)
        mdl.write_ushort(self.normal)

class MD3Surface:
    BaseSize = MaxPath + (4 * 11)

    def __init__(self, name=''):
        self.name = name
        self.flags = 0
        self.shaders = []
        self.triangles = []
        self.texcoords = []
        self.verts = []
    def read(self, mdl):
        ident = mdl.read_string(4)
        if ident != "IDP3":
            self.file.close()
            return None
        self.name = mdl.read_path(MaxPath)
        self.flags = mdl.read_int()

        num_frames = mdl.read_int()
        num_shaders = mdl.read_int()
        num_verts = mdl.read_int()
        num_triangles = mdl.read_int()

        ofs_triangles = mdl.read_int()
        ofs_shaders = mdl.read_int()
        ofs_st = mdl.read_int()
        ofs_xyznormal = mdl.read_int()
        ofs_eof = mdl.read_int()

        for _ in range(num_triangles):
            self.triangles.append(MD3Triangle().read(mdl))
        for _ in range(num_shaders):
            self.shaders.append(MD3Shader().read(mdl))
        for _ in range(num_verts):
            self.texcoords.append(MD3TexCoord().read(mdl))
        for _ in range(num_verts * num_frames):
            self.verts.append(MD3Vertex().read(mdl))
        return self
    def write(self, mdl):
        mdl.write_string(mdl.ident, 4)
        mdl.write_path(self.name, MaxPath)
        mdl.write_int(self.flags)

        mdl.write_int(len(mdl.frames))
        mdl.write_int(len(self.shaders))
        mdl.write_int(len(self.verts) // len(mdl.frames))
        mdl.write_int(len(self.triangles))

        ofs_triangles = MD3Surface.BaseSize
        ofs_shaders = ofs_triangles + (MD3Triangle.Size * len(self.triangles))
        ofs_st = ofs_shaders + (MD3Shader.Size * len(self.shaders))
        ofs_xyznormal = ofs_st + (MD3TexCoord.Size * len(self.texcoords))
        ofs_eof = ofs_xyznormal + (MD3Vertex.Size * len(self.verts))

        mdl.write_int(ofs_triangles)
        mdl.write_int(ofs_shaders)
        mdl.write_int(ofs_st)
        mdl.write_int(ofs_xyznormal)
        mdl.write_int(ofs_eof)

        for tri in self.triangles:
            tri.write(mdl)
        for shader in self.shaders:
            shader.write(mdl)
        for tc in self.texcoords:
            tc.write(mdl)
        for v in self.verts:
            v.write(mdl)

    def calculate_size(self):
        return MD3Surface.BaseSize + (MD3Shader.Size * len(self.shaders)) + (MD3Triangle.Size * len(self.triangles)) + (MD3TexCoord.Size * len(self.texcoords)) + (MD3Vertex.Size * len(self.verts))

class MD3:
    def read_byte(self, count=1):
        size = 1 * count
        data = self.file.read(size)
        data = unpack("<%dB" % count, data)
        if count == 1:
            return data[0]
        return data

    def read_int(self, count=1):
        size = 4 * count
        data = self.file.read(size)
        data = unpack("<%di" % count, data)
        if count == 1:
            return data[0]
        return data

    def read_short(self, count=1):
        size = 2 * count
        data = self.file.read(size)
        data = unpack("<%dh" % count, data)
        if count == 1:
            return data[0]
        return data

    def read_ushort(self, count=1):
        size = 2 * count
        data = self.file.read(size)
        data = unpack("<%dH" % count, data)
        if count == 1:
            return data[0]
        return data

    def read_float(self, count=1):
        size = 4 * count
        data = self.file.read(size)
        data = unpack("<%df" % count, data)
        if count == 1:
            return data[0]
        return data

    def read_bytes(self, size):
        return self.file.read(size)

    def read_string(self, size):
        data = self.file.read(size)
        s = ""
        for c in data:
            s = s + chr(c)
        return s

    def write_byte(self, data):
        if not hasattr(data, "__len__"):
            data = (data,)
        self.file.write(pack(("<%dB" % len(data)), *data))

    def write_int(self, data):
        if not hasattr(data, "__len__"):
            data = (data,)
        self.file.write(pack(("<%di" % len(data)), *data))

    def write_short(self, data):
        if not hasattr(data, "__len__"):
            data = (data,)
        self.file.write(pack(("<%dh" % len(data)), *data))

    def write_ushort(self, data):
        if not hasattr(data, "__len__"):
            data = (data,)
        self.file.write(pack(("<%dH" % len(data)), *data))

    def write_float(self, data):
        if not hasattr(data, "__len__"):
            data = (data,)
        self.file.write(pack(("<%df" % len(data)), *data))

    def write_bytes(self, data, size=-1):
        if size == -1:
            size = len(data)
        self.file.write(data[:size])
        if size > len(data):
            self.file.write(bytes(size - len(data)))

    def write_string(self, data, size=-1):
        data = data.encode()
        self.write_bytes(data, size)

    def read_path(self, len):
        name = self.read_string(len)
        if "\0" in name:
            name = name[:name.index("\0")]
        return name

    def write_path(self, path, len):
        self.write_string(path, len)

    def __init__(self, name="md3"):
        self.ident = "IDP3"
        self.version = 15
        self.name = name
        self.flags = 0
        self.frames = []
        self.tags = []
        self.surfaces = []

    def calculate_surface_size(self):
        size = 0
        for surf in self.surfaces:
            size += surf.calculate_size()
        return size

    def read(self, filepath):
        self.file = open(filepath, "rb")
        self.ident = self.read_string(4)
        self.version = self.read_int()
        if self.ident != "IDP3" or self.version != 15:
            self.file.close()
            return None

        self.name = self.read_path(MaxPath)
        self.flags = self.read_int()

        num_frames = self.read_int()
        num_tags = self.read_int()
        num_surfs = self.read_int()
        self.read_int()

        ofs_frames = self.read_int()
        ofs_tags = self.read_int()
        ofs_surfaces = self.read_int()
        ofs_eof = self.read_int()

        self.file.seek(ofs_frames)

        for _ in range(num_frames):
            self.frames.append(MD3Frame().read(self))

        self.file.seek(ofs_tags)

        for _ in range(num_tags):
            self.tags.append(MD3Tag().read(self))

        self.file.seek(ofs_surfaces)

        for _ in range(num_surfs):
            self.surfaces.append(MD3Surface().read(self))

        self.file.close()
        return self
    
    def write(self, filepath):
        self.file = open(filepath, "wb")
        self.write_string(self.ident, 4)
        self.write_int(self.version)
        self.write_path(self.name, MaxPath)
        self.write_int(self.flags)

        self.write_int(len(self.frames))
        self.write_int(len(self.tags))
        self.write_int(len(self.surfaces))
        self.write_int(0)

        ofs_frames = self.file.tell() + (4 * 4)
        ofs_tags = ofs_frames + (MD3Frame.Size * len(self.frames))
        ofs_surfaces = ofs_tags + (MD3Tag.Size * len(self.tags))
        ofs_eof = ofs_surfaces + self.calculate_surface_size()

        self.write_int(ofs_frames)
        self.write_int(ofs_tags)
        self.write_int(ofs_surfaces)
        self.write_int(ofs_eof)

        for frame in self.frames:
            frame.write(self)
        for tag in self.tags:
            tag.write(self)
        for surf in self.surfaces:
            surf.write(self)

        self.file.close()