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

class MD2:
    class Skin:
        def __init__(self, name=''):
            self.name = name
        def read(self, mdl):
            self.name = mdl.read_path()
            return self
        def write(self, mdl):
            mdl.write_path(self.name)

    class STVert:
        def __init__(self, st=None):
            if not st:
                st = (0, 0)
            self.s, self.t = st
            pass
        def read(self, mdl):
            self.s, self.t = mdl.read_short(2)
            return self
        def write(self, mdl):
            mdl.write_short((self.s, self.t))

    class Tri:
        def __init__(self, verts=None, tcs=None):
            if not verts:
                verts = (0, 0, 0)
            if not tcs:
                tcs = (0, 0, 0)
            self.verts = verts
            self.tcs = tcs
        def read(self, mdl):
            self.verts = mdl.read_short(3)
            self.tcs = mdl.read_short(3)
            return self
        def write(self, mdl):
            mdl.write_short(self.verts)
            mdl.write_short(self.tcs)

    class Frame:
        def __init__(self):
            self.scale = [0, 0, 0]
            self.translate = [0, 0, 0]
            self.name = ""
            self.verts = []
        def add_vert(self, vert: 'Vert'):
            self.verts.append(vert)
        def calc_scale(self):
            # only used for writing
            mins = [9999, 9999, 9999]
            maxs = [-9999, -9999, -9999]

            for vert in self.verts:
                for i, v in enumerate(vert.r):
                    mins[i] = min(mins[i], v)
                    maxs[i] = max(maxs[i], v)
            self.scale = tuple(map(lambda x: x / 255.0, (Vector(maxs) - Vector(mins))))
            self.translate = mins
        def scale_verts(self):
            for vert in self.verts:
                vert.scale(self)
        def read(self, mdl: 'MD2', numverts):
            self.read_bounds(mdl)
            self.read_name(mdl)
            self.read_verts(mdl, numverts)
            return self
        def write(self, mdl: 'MD2'):
            self.write_bounds(mdl)
            self.write_name(mdl)
            self.write_verts(mdl)
        def read_name(self, mdl: 'MD2'):
            name = mdl.read_string(16)
            if "\0" in name:
                name = name[:name.index("\0")]
            self.name = name
        def write_name(self, mdl: 'MD2'):
            mdl.write_string(self.name, 16)
        def read_bounds(self, mdl: 'MD2'):
            self.scale = mdl.read_float(3)
            self.translate = mdl.read_float(3)
        def write_bounds(self, mdl: 'MD2'):
            mdl.write_float(self.scale)
            mdl.write_float(self.translate)
        def read_verts(self, mdl: 'MD2', num):
            self.verts = []
            for i in range(num):
                self.verts.append(MD2.Vert().read(mdl))
        def write_verts(self, mdl: 'MD2'):
            for vert in self.verts:
                vert.write(mdl)

    class Vert:
        def __init__(self, r=None, ni=0):
            if not r:
                r = (0, 0, 0)
            self.r = r
            self.ni = ni
            pass
        def read(self, mdl):
            self.r = mdl.read_byte(3)
            self.ni = mdl.read_byte()
            return self
        def write(self, mdl):
            r = tuple(map(lambda a: int(a) & 255, self.r))
            mdl.write_byte(r)
            mdl.write_byte(self.ni)
        def scale(self, frame):
            old_r = self.r
            self.r = tuple(map(lambda x, s, t: (x - t) / s,
                               self.r, frame.scale, frame.translate))

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

    def read_path(self):
        name = self.read_string(64)
        if "\0" in name:
            name = name[:name.index("\0")]
        return name

    def write_path(self, path):
        self.write_string(path, 64)

    def __init__(self, name = "md2"):
        self.name = name
        self.ident = "IDP2"
        self.version = 8
        self.skinwidth = 0
        self.skinheight = 0
        self.framesize = 0
        self.skins = []
        self.stverts = []
        self.tris = []
        self.frames = []
        pass
    def read(self, filepath):
        self.file = open(filepath, "rb")
        self.name = filepath.split('/')[-1]
        self.name = self.name.split('.')[0]
        self.ident = self.read_string(4)
        self.version = self.read_int()
        if self.ident != "IDP2" or self.version != 8:
            return None
        self.skinwidth, self.skinheight = self.read_int(2)
        framesize = self.read_int()
        numskins, numverts, numst, numtris, numglcmds, numframes = self.read_int(6)
        ofskins, ofst, oftris, offrames, ofglcmds, ofend = self.read_int(6)
        # read in the skin data
        self.skins = []
        self.file.seek(ofskins)
        for i in range(numskins):
            self.skins.append(MD2.Skin().read(self))
        #read in the st verts (uv map)
        self.stverts = []
        self.file.seek(ofst)
        for i in range(numst):
            self.stverts.append(MD2.STVert().read(self))
        #read in the tris
        self.tris = []
        self.file.seek(oftris)
        for i in range(numtris):
            self.tris.append(MD2.Tri().read(self))
        #read in the frames
        self.frames = []
        self.file.seek(offrames)
        for i in range(numframes):
            self.frames.append(MD2.Frame().read(self, numverts))
        return self

    def write(self, filepath):
        self.file = open(filepath, "wb")
        self.write_string(self.ident, 4)
        self.write_int(self.version)
        self.write_int((self.skinwidth, self.skinheight))
        framesize = 40 + (4 * len(self.frames[0].verts))
        self.write_int(framesize)
        self.write_int(len(self.skins))
        self.write_int(len(self.frames[0].verts))
        self.write_int(len(self.stverts))
        self.write_int(len(self.tris))
        self.write_int(0)
        self.write_int(len(self.frames))
        pos = self.file.tell() + (6 * 4)
        self.write_int(pos) # skin offset
        pos += 64 * len(self.skins)
        self.write_int(pos) # st offset
        pos += 4 * len(self.stverts)
        self.write_int(pos) # tris offset
        pos += 12 * len(self.tris)
        self.write_int(pos) # frame offset
        pos += framesize * len(self.frames)
        self.write_int(pos) # glcmds
        self.write_int(pos) # end
        # write out the skin data
        for skin in self.skins:
            skin.write(self)
        #write out the st verts (uv map)
        for st in self.stverts:
            st.write(self)
        #write out the tris
        for tri in self.tris:
            tri.write(self)
        #write out the frames
        for frame in self.frames:
            frame.write(self)
