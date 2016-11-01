'''
    ZeroEngine .msh model format parser.

    Refer to
       schlechtwetterfront.github.io/ze_filetypes/msh.html
   for more information regarding the file format.
'''
import msh2
reload(msh2)
from struct import unpack as unpack
import logging

STR_CODEC = 'utf-8'
CHUNK_LIST = ['HEDR', 'SHVO', 'MSH2',
              'SINF', 'FRAM', 'CAMR',
              'MATL', 'DATA', 'MATD', 'ATRB', 'TX0D', 'TX1D', 'TX2D', 'TX3D',
              'MODL', 'MTYP', 'MNDX', 'PRNT', 'FLGS', 'TRAN', 'ENVL', 'SWCI',
              'GEOM', 'SEGM', 'SHDW', 'MATI', 'POSL', 'NRML', 'UV0L', 'CLRL',
              'CLRB', 'WGHT', 'NDXL', 'NDXT', 'STRP',
              'CLTH', 'CTEX', 'CPOS', 'CUV0', 'FIDX', 'FWGT', 'SPRS', 'CPRS',
              'BPRS', 'COLL',
              'SKL2', 'BLN2', 'ANM2', 'CYCL', 'KFR3',
              'NAME', 'BBOX', 'CL1L']


class UnpackError(Exception):
    def __init__(self, val):
        self.val = val

    def __str__(self):
        return str(self.val)


class Unpacker(object):
    def unpack_header(self, data):
        return data[:4], unpack('<L', data[4:])[0]

    def unpack_str(self, data):
        pass

    def log(self, text):
        logging.debug(text)

    def dont_log(self, *text):
        pass

    def long(self, data):
        return unpack('<L', data)[0]

    def short(self, data):
        return unpack('<H', data)[0]

    def float(self, data):
        return unpack('<f', data)[0]


class BBoxUnpacker(Unpacker):
    def __init__(self, data):
        self.bbox = msh2.BBox()
        self.data = data

    def unpack(self):
        self.bbox.rotation = unpack('<ffff', self.data[:16])
        self.bbox.center = unpack('<fff', self.data[16:28])
        self.bbox.extents = unpack('<fff', self.data[28:40])
        self.bbox.radius = unpack('<f', self.data[40:])[0]
        return self.bbox


class MSHUnpack(Unpacker):
    def __init__(self, mshfile, config={'do_logging': False,
                                        'ignore_geo': False,
                                        'triangulate': False}):
        self.mshfile = mshfile
        self.msh = msh2.Msh()
        self.msh.animation = msh2.Animation(self.msh, 'maybe_empty')
        self.config = config
        if not config['do_logging']:
            self.log = self.dont_log

    def unpack(self):
        with open(self.mshfile, 'rb') as mf:
            # HEDR
            bin, self.size = self.unpack_header(mf.read(8))
            # MSH2 or SHVO
            bin, self.msh2size = self.unpack_header(mf.read(8))
            if bin == 'SHVO':
                self.log('Skipping SHVO chunk.')
                # Read the 4 content bytes of SHVO.
                mf.read(4)
                # that's definitely MSH2
                bin, self.msh2size = self.unpack_header(mf.read(8))
            mdlcoll = msh2.ModelCollection(self.msh)
            self.msh.models = mdlcoll
            while True:
                hdr, size = self.unpack_header(mf.read(8))
                self.log('Header, Size: {0}, {1}'.format(hdr, size))
                if hdr == 'SINF':
                    si = InfoUnpacker(self, size, mf)
                    self.msh.info = si.unpack()
                elif hdr == 'MATL':
                    num_materials = unpack('<L', mf.read(4))[0]
                    matcoll = msh2.MaterialCollection(self.msh)
                    for n in xrange(num_materials):
                        mat, matsize = self.unpack_header(mf.read(8))
                        self.log('Material, Size: {0}, {1}'.format(mat, matsize))
                        mat = MaterialUnpacker(self, matsize, mf)
                        matcoll.add(mat.unpack())
                    matcoll.assign_indices()
                    self.msh.materials = matcoll
                elif hdr == 'MODL':
                    mdl = ModelUnpacker(self, size, mf)
                    mdlcoll.add(mdl.unpack())
                elif hdr == 'CAMR':
                    mf.read(size)
                elif hdr == 'LGHT':
                    mf.read(size)
                elif hdr == 'SKL2':
                    numbones = unpack('<L', mf.read(4))[0]
                    bonecoll = msh2.BoneCollection(self.msh.animation)
                    for n in xrange(numbones):
                        bone = msh2.Bone(bonecoll)
                        bone.CRC = mf.read(4)
                        bone.set_name_from_crc()
                        bone.bone_type = unpack('<L', mf.read(4))[0]
                        bone.constrain = unpack('<f', mf.read(4))[0]
                        bone.bone1len = unpack('<f', mf.read(4))[0]
                        bone.bone2len = unpack('<f', mf.read(4))[0]
                        bonecoll.add(bone)
                    self.msh.animation.bones = bonecoll
                elif hdr == 'BLN2':
                    # Ignore BLN2 as this only has one attribute(blend_factor).
                    # It's not clear which type this is and it's not important.
                    mf.read(size)
                elif hdr == 'ANM2':
                    # Continue as this is only a header.
                    continue
                elif hdr == 'CYCL':
                    num_cycles = unpack('<L', mf.read(4))[0]
                    cycles = []
                    for n in xrange(num_cycles):
                        cycle = msh2.Cycle(self.msh.animation)
                        cycle.name = mf.read(64).strip('\x00')
                        cycle.fps = unpack('<f', mf.read(4))[0]
                        cycle.style = unpack('<L', mf.read(4))[0]
                        cycle.frames = unpack('<LL', mf.read(8))
                        cycles.append(cycle)
                    self.msh.animation.cycles = cycles
                    self.msh.animation.cycle = cycles[0]
                elif hdr == 'KFR3':
                    numbones = unpack('<L', mf.read(4))[0]
                    for n in xrange(numbones):
                        # Ingore the crc, usually the same order as before.
                        mf.read(4)
                        bone = self.msh.animation.bones[n]
                        bone.keyframe_type = unpack('<L', mf.read(4))[0]
                        numtran, numrot = unpack('<LL', mf.read(8))
                        tran = []
                        translation_frame_indices = []
                        rot = []
                        rotation_frame_indices = []
                        for i in xrange(numtran):
                            # Ignore the frame index.
                            translation_frame_indices.append(unpack('<L', mf.read(4))[0])
                            # Add X, Y, Z position tuple.
                            tran.append(unpack('<fff', mf.read(12)))
                        for i in xrange(numrot):
                            # Again, ignore the frame index.
                            rotation_frame_indices.append(unpack('<L', mf.read(4))[0])
                            # X, Y, Z, W quaternion translation tuple.
                            rot.append(unpack('<ffff', mf.read(16)))
                        bone.pos_keyframes = tran
                        bone.pos_keyframe_indices = translation_frame_indices
                        bone.rot_keyframes = rot
                        bone.rot_keyframe_indices = rotation_frame_indices
                elif hdr == 'CL1L':
                    break
                else:
                    self.log('Unrecognized chunk {0} in MSHUnpack.'.format(hdr))
                    raise UnpackError('Unrecognized chunk {0} in MSHUnpack (can be a valid chunk but doesnt fit into this unpack level).'.format(hdr))
                    break
        for model in self.msh.models:
            model.set_deformers_from_indices()
        return self.msh


class ModelUnpacker(Unpacker):
    def __init__(self, up, size, fh):
        self.size = size
        self.fh = fh
        self.mdl = msh2.Model(up.msh)
        self.up = up
        self.log = up.log

    def unpack(self):
        self.log('Unpacking Model at {0}.'.format(self.fh.tell() - 8))
        while True:
            hdr, size = self.unpack_header(self.fh.read(8))
            self.log('Model: Header, Size: {0}, {1}'.format(hdr, size))
            if hdr == 'MTYP':
                self.mdl.model_type = msh2.MODEL_TYPES_INT[unpack('<L', self.fh.read(4))[0]]
            # RepSharpshooters MshEx exports MTYP as MYTP. Should work since the format update.
            elif hdr == 'MYTP':
                logging.info('Found RepSharpshooter MshEx type .msh. Continuing the import.')
                self.mdl.model_type = msh2.MODEL_TYPES_INT[unpack('<L', self.fh.read(4))[0]]
            elif hdr == 'NAME':
                self.mdl.name = self.fh.read(size).strip('\x00')
            elif hdr == 'MNDX':
                self.mdl.index = unpack('<L', self.fh.read(4))[0]
            elif hdr == 'PRNT':
                self.mdl.parent_name = self.fh.read(size).strip('\x00').encode(STR_CODEC)
            elif hdr == 'FLGS':
                self.mdl.vis = unpack('<L', self.fh.read(4))[0]
            elif hdr == 'TRAN':
                scl = unpack('<fff', self.fh.read(12))
                rot = unpack('<ffff', self.fh.read(16))
                tra = unpack('<fff', self.fh.read(12))
                self.mdl.transform = msh2.Transform(tra, rot, scl)
            elif hdr == 'GEOM':
                if self.up.config['ignore_geo']:
                    self.fh.read(size)
                    continue
                # If this is a bone(MTYP 3) then set model type to geobone as
                # it has geometry, too.
                if self.mdl.model_type == 'bone':
                    self.mdl.model_type = 'geobone'
                # Ignore the bbox header and size indicator. We dont need it.
                self.fh.read(8)
                bb = BBoxUnpacker(self.fh.read(44))
                self.mdl.bbox = bb.unpack()
                self.mdl.segments = msh2.SegmentCollection(self.mdl)
                while True:
                    soc, ssize = self.unpack_header(self.fh.read(8))
                    self.log('Model Segments: Header, Size: {0}, {1}'.format(soc, ssize))
                    if soc == 'SEGM':
                        segm = GeometryUnpacker(self, ssize, self.fh)
                        self.mdl.segments.add(segm.unpack())
                    elif soc == 'CLTH':
                        segm = ClothUnpacker(self, ssize, self.fh)
                        self.mdl.segments.add(segm.unpack())
                    elif soc == 'ENVL':
                        num = unpack('<L', self.fh.read(4))[0]
                        inds = []
                        for n in xrange(num):
                            inds.append(unpack('<L', self.fh.read(4))[0])
                        self.mdl.deformer_indices = inds
                    else:
                        self.log('Unrecognized chunk {0} in ModelUnpack(Geometry).'.format(soc))
                        self.fh.seek(self.fh.tell() - 8)
                        break
            elif hdr == 'SWCI':
                self.mdl.collprim = True
                prim_data = unpack('<Lfff', self.fh.read(16))
                self.mdl.primitive = (prim_data[0], prim_data[1],
                                      prim_data[2], prim_data[3])
            else:
                self.log('Unrecognized chunk {0} in ModelUnpack.'.format(hdr))
                # Return to the position before the header.
                self.fh.seek(self.fh.tell() - 8)
                break
        return self.mdl


class ClothUnpacker(Unpacker):
    def __init__(self, up, size, fh):
        self.up = up
        self.size = size
        self.fh = fh
        self.seg = msh2.ClothGeometry(up.mdl)
        self.log = up.log

    def unpack(self):
        self.log('Unpacking Cloth.')
        fixed = []
        while True:
            hdr, size = self.unpack_header(self.fh.read(8))
            logging.debug('Cloth: Header, Size: {0}, {1}'.format(hdr, size))
            if hdr == 'CTEX':
                self.seg.texture = self.fh.read(size).strip('\x00').encode(STR_CODEC)
            elif hdr == 'CPOS':
                vertcoll = msh2.ClothVertexCollection(self.seg)
                num = unpack('<L', self.fh.read(4))[0]
                for n in xrange(num):
                    pos = unpack('<fff', self.fh.read(12))
                    vert = msh2.ClothVertex(pos)
                    vertcoll.add(vert)
                self.seg.vertices = vertcoll
            elif hdr == 'CUV0':
                num = unpack('<L', self.fh.read(4))[0]
                for n in xrange(num):
                    self.seg.vertices[n].uv = unpack('<ff', self.fh.read(8))
            elif hdr == 'FIDX':
                num = unpack('<L', self.fh.read(4))[0]
                for n in xrange(num):
                    index = unpack('<L', self.fh.read(4))[0]
                    fixed.append(index)
                    self.seg.vertices[index].is_fixed = True
            elif hdr == 'FWGT':
                self.fh.read(4)  # Number of points.
                weights = self.fh.read(size - 4).split('\x00')
                logging.debug('Cloth Deformers: {0}'.format(weights))
                logging.debug('Cloth Fixed Points: {0}'.format(len(fixed)))
                weights.remove('')
                if len(weights) > 0:
                    for index, vertindex in enumerate(fixed):
                        self.seg.vertices[vertindex].deformer = weights[index]
            elif hdr == 'CMSH':
                num = unpack('<L', self.fh.read(4))[0]
                facecoll = msh2.FaceCollection(self.seg)
                for n in xrange(num):
                    face = msh2.Face()
                    face.vertices = unpack('<LLL', self.fh.read(12))
                    facecoll.add(face)
                self.seg.faces = facecoll
            elif hdr == 'SPRS':
                num_constraints = self.long(self.fh.read(4))
                s_constraints = []
                for n in xrange(num_constraints):
                    s_constraints.append(unpack('<HH', self.fh.read(4)))
                self.seg.stretch_constraints = s_constraints
            elif hdr == 'CPRS':
                num_constraints = self.long(self.fh.read(4))
                c_constraints = []
                for n in xrange(num_constraints):
                    c_constraints.append(unpack('<HH', self.fh.read(4)))
                self.seg.cross_constraints = c_constraints
            elif hdr == 'BPRS':
                num_constraints = self.long(self.fh.read(4))
                b_constraints = []
                for n in xrange(num_constraints):
                    b_constraints.append(unpack('<HH', self.fh.read(4)))
                self.seg.bend_constraints = b_constraints
            elif hdr == 'COLL':
                num_colls = self.long(self.fh.read(4))
                for n in xrange(num_colls):
                    collision = msh2.ClothCollision()
                    collision.cloth = self.seg
                    name = []
                    while 1:
                        char = self.fh.read(1)
                        if char == '\x00':
                            break
                        name.append(char)
                    collision.name = ''.join(name)
                    parent = []
                    while 1:
                        char = self.fh.read(1)
                        if char == '\x00':
                            break
                        parent.append(char)
                    collision.parent = ''.join(parent)
                    collision.primitive_type = unpack('<L', self.fh.read(4))[0]
                    collision.primitive_data = unpack('<fff', self.fh.read(12))
                    self.seg.collisions.append(collision)
                # COLL chunk seems to be padded with \x00 at the end to get an even size indicator.
                while True:
                    if self.fh.read(1) == '\x00':
                        continue
                    else:
                        self.fh.seek(self.fh.tell() - 1)
                        break
            else:
                self.log('Unrecognized chunk {0} in ClothUnpack.'.format(hdr))
                # Return to the position before the header.
                self.fh.seek(self.fh.tell() - 8)
                break
        return self.seg


class GeometryUnpacker(Unpacker):
    def __init__(self, up, size, fh):
        self.up = up
        self.size = size
        self.fh = fh
        # Either SegmentGeometry or ShadowGeometry.
        # Usually it's SegmentGeometry so we'll set it as default.
        # Cloth doesn't have the SEGM chunk we read before we got here.
        self.seg = msh2.SegmentGeometry(up.mdl)
        self.log = up.log

    def unpack(self):
        # Now we have to check which type of segment it is.
        # Most common will be static meshes, then maybe shadows,
        # then enveloped.
        # Enveloped and static meshes share most of the chunks,
        # however, shadows meshes only have one chunk.
        self.log('Unpacking Geometry.')
        self.up.up.last_chunk = None
        while True:
            # The SEGM header is already gone so read the next one.
            hdr, size = self.unpack_header(self.fh.read(8))
            self.log('Geo: Header, Size: {0}, {1}'.format(hdr, size))
            if hdr == 'SHDW':
                self.up.up.last_chunk = 'SHDW'
                self.seg = msh2.ShadowGeometry(self.up.mdl)
                # self.seg.data = self.fh.read(size)
                num_pos = self.long(self.fh.read(4))
                positions = []
                for n in xrange(num_pos):
                    positions.append((self.float(self.fh.read(4)), self.float(self.fh.read(4)), self.float(self.fh.read(4))))
                num_edges = self.long(self.fh.read(4))
                edges = []
                for n in xrange(num_edges):
                    edge = self.short(self.fh.read(2)), self.short(self.fh.read(2)), self.short(self.fh.read(2)), self.short(self.fh.read(2))
                    edges.append(edge)
                self.seg.positions = positions
                self.seg.edges = edges
            elif hdr == 'MATI':
                self.up.up.last_chunk = 'MATI'
                # 1st up: ModelUnpacker, 2nd up: MSHUnpack
                self.seg.material = self.up.up.msh.get_mat_by_index(unpack('<L', self.fh.read(4))[0])
                self.seg.mat_name = self.seg.material.name
            elif hdr == 'POSL':
                self.up.up.last_chunk = 'POSL'
                num_positions = unpack('<L', self.fh.read(4))[0]
                vertcoll = msh2.VertexCollection(self.seg)
                for n in xrange(num_positions):
                    pos = self.fh.read(12)
                    pos = unpack('<fff', pos)
                    vert = msh2.Vertex(pos)
                    vertcoll.add(vert)
                self.seg.vertices = vertcoll
            elif hdr == 'NRML':
                self.up.up.last_chunk = 'NRML'
                num_normals = unpack('<L', self.fh.read(4))[0]
                for n in xrange(num_normals):
                    self.seg.vertices[n].normal = unpack('<fff', self.fh.read(12))
            elif hdr == 'UV0L':
                self.up.up.last_chunk = 'UV0L'
                num_uvs = unpack('<L', self.fh.read(4))[0]
                for n in xrange(num_uvs):
                    self.seg.vertices[n].uv = unpack('<ff', self.fh.read(8))
                self.seg.vertices.uved = True
            elif hdr == 'CLRL':
                self.up.up.last_chunk = 'CLRL'
                num_colors = unpack('<L', self.fh.read(4))[0]
                for n in xrange(num_colors):
                    self.seg.vertices[n].color = msh2.Color(unpack('<BBBB', self.fh.read(4)))
                self.seg.vertices.colored = True
            elif hdr == 'CLRB':
                self.up.up.last_chunk = 'CLRB'
                color = unpack('<BBBB', self.fh.read(4))
                for vert in self.seg.vertices:
                    vert.color = msh2.Color(color)
                self.seg.vertices.colored = True
            elif hdr == 'WGHT':
                last_chunk = 'WGHT'
                num = unpack('<L', self.fh.read(4))[0]
                for n in xrange(num):
                    indices = []
                    vals = []
                    for i in xrange(4):
                        indices.append(unpack('<L', self.fh.read(4))[0])
                        vals.append(unpack('<f', self.fh.read(4))[0])
                    self.seg.vertices[n].deformer_indices = indices
                    self.seg.vertices[n].weights = vals
                self.seg.vertices.weighted = True
            elif hdr == 'STRP':
                last_chunk = 'STRP'
                num = unpack('<L', self.fh.read(4))[0]
                facecoll = msh2.FaceCollection(self.seg)
                num_begins = 0
                for n in xrange(num):
                    val = unpack('<H', self.fh.read(2))[0]
                    if (val - 0x8000) > -1:
                        if num_begins == 0:
                            num_begins += 1
                            face = msh2.Face()
                            facecoll.add(face)
                        elif num_begins == 1:
                            num_begins += 1
                            if face.sides > 2:
                                face = msh2.Face()
                                facecoll.add(face)
                                num_begins = 0
                        elif num_begins == 2:
                            num_begins = 1
                            face = msh2.Face()
                            facecoll.add(face)
                        face.add(val - 0x8000)
                    else:
                        face.add(val)
                facecoll.de_ngonize(self.up.up.config['triangulate'])
                self.seg.faces = facecoll
            elif hdr == 'NDXL':
                last_chunk = 'NDXL'
                self.fh.read(size)
            elif hdr == 'NDXT':
                last_chunk = 'NDXT'

                # If the faces are already set (for example from the STRP chunk)
                # then ignore this as it's usually deprecated.
                if self.seg.faces:
                    continue

                num_triangles = unpack('<L', self.fh.read(4))[0]

                logging.info('Sizes: %d == %d', num_triangles * 6 + 4, size)

                faces = msh2.FaceCollection(self.seg)

                for n in range(num_triangles):
                    face = msh2.Face(list(unpack('<HHH', self.fh.read(2 * 3))))
                    faces.add(face)

                self.seg.faces = faces
            else:
                if hdr not in CHUNK_LIST:
                    if last_chunk == 'STRP':
                        self.log('Fixing STRP chunk import.')
                        self.fh.seek(self.fh.tell() - 8)
                        self.fh.read(2)
                        continue
                self.log('Unrecognized chunk {0} in GeometryUnpack.'.format(hdr))
                # Return to the position before the header.
                self.fh.seek(self.fh.tell() - 8)
                break
        return self.seg


class MaterialUnpacker(Unpacker):
    def __init__(self, up, size, fh):
        self.size = size
        self.fh = fh
        self.mat = msh2.Material(up.msh)
        self.log = up.log

    def unpack(self):
        self.log('Unpacking Material.')
        # NAME chunk.
        bin, size = self.unpack_header(self.fh.read(8))
        bin, size
        self.mat.name = self.fh.read(size).strip('\x00')
        self.mat.name
        # DATA chunk.
        self.fh.read(8)
        self.mat.diff_color = msh2.Color(unpack('<ffff', self.fh.read(16)))
        self.mat.spec_color = msh2.Color(unpack('<ffff', self.fh.read(16)))
        self.mat.ambt_color = msh2.Color(unpack('<ffff', self.fh.read(16)))
        self.mat.gloss = unpack('<f', self.fh.read(4))[0]
        # ATRB chunk.
        self.fh.read(8)
        self.mat.flags = self.mat.flags_from_int(unpack('<B', self.fh.read(1))[0])
        self.mat.render_type, self.mat.data0, self.mat.data1 = unpack('<BBB', self.fh.read(3))
        # Textures.
        for n in xrange(4):
            hdr, size = self.unpack_header(self.fh.read(8))
            self.log('TX header, size: {0}, {1}'.format(hdr, size))
            if hdr[:2] == 'TX':
                if hdr[2] == '0':
                    self.mat.tex0 = self.fh.read(size).strip('\x00').encode(STR_CODEC)
                elif hdr[2] == '1':
                    self.mat.tex1 = self.fh.read(size).strip('\x00').encode(STR_CODEC)
                elif hdr[2] == '2':
                    self.mat.tex2 = self.fh.read(size).strip('\x00').encode(STR_CODEC)
                elif hdr[2] == '3':
                    self.mat.tex3 = self.fh.read(size).strip('\x00').encode(STR_CODEC)
            else:
                self.log('Unrecognized chunk {0} in MaterialUnpacker.'.format(hdr))
                self.fh.seek(self.fh.tell() - 8)
                break
        return self.mat


class InfoUnpacker(Unpacker):
    def __init__(self, up, size, fh):
        self.size = size
        self.fh = fh
        self.info = msh2.SceneInfo(up.msh)
        self.log = up.log

    def unpack(self):
        self.log('Unpacking Scene Info.')
        # Name chunk.
        bin, size = self.unpack_header(self.fh.read(8))
        self.info.name = self.fh.read(size).strip('\x00').encode(STR_CODEC)
        # FRAM chunk.
        bin, size = self.unpack_header(self.fh.read(8))
        self.info.frame_range = unpack('<LL', self.fh.read(8))
        self.info.fps = unpack('<f', self.fh.read(4))[0]
        # BBOX chunk.
        self.fh.read(8)  # Just read those, size is always the same.
        bb = BBoxUnpacker(self.fh.read(44))
        self.info.bbox = bb.unpack()
        return self.info
