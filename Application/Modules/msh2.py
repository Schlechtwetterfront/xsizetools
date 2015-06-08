# -*- encoding: ascii -*-
#########################################################
#####                    msh2                       #####
#####                                               #####
#####             MSH2 Framework main               #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####       http://byentech.wordpress.com           #####
#########################################################
import msh2_crc
reload(msh2_crc)
import itertools
import struct
import math
import logging
import json
import os


MODEL_TYPES = {'null': 0,
               'geodynamic': 1,
               'cloth': 2,
               'bone': 3,
               'geobone': 3,
               'geostatic': 4,
               'geoshadow': 6}

MODEL_TYPES_INT = ['null',
                   'geodynamic',
                   'cloth',
                   'bone',
                   'geostatic',
                   '',
                   'geoshadow']


class MSH2Error(Exception):
    def __init__(self, value):
        self.parameter = value

    def __str__(self):
        return repr(self.parameter)


class Packer(object):
    def pad_string(self, string):
        '''Pads the given string with \x00s to fill a multiple of 4 length.'''
        if string == '':
            return ''
        i = 0
        while len(string) >= i:
            i += 4
        return string.ljust(i, '\x00')

    def null_terminate(self, string):
        '''Null-terminates the given string string.'''
        return string + '\x00'

    def pack_long_chunk(self, header, number):
        '''Chunk with only one long int.'''
        data = [header]
        data.append(struct.pack('<L', 4))
        data.append(struct.pack('<L', number))
        return ''.join(data)

    def pack_string_chunk(self, header, string):
        '''String Chunk(NAME, TX0D...) packer.'''
        data = [header]
        comp_str = self.pad_string(string.encode('ascii'))
        data.append(struct.pack('<L', len(comp_str)))
        data.append(comp_str)
        return ''.join(data)

    def sum_seq(self, seq, start=0, end=None):
        '''Sums the sequence items from start to end.
        If end is None it will sum all items from start.'''
        if end:
            tosum = seq[start:end]
        else:
            tosum = seq[start:]
        tosum = [len(item) for item in tosum]
        return sum(tosum)


class Msh(Packer):
    # is_shadowvolume bool
    # info Info
    # materials Material[]
    # models Model[]
    # animation Animation
    def __init__(self):
        self.info = None
        self.has_shadowvolume = False
        self.models = []
        self.materials = []
        self.animation = None
        self.classname = 'Msh'
        self.modulepath = ''

    def dump(self, filepath):
        '''Dumps .msh file information into a text file.'''
        with open(filepath, 'w') as fh:
            self.info.dump(fh)
            self.materials.dump(fh)
            self.models.dump(fh)
        return True

    def save(self, filepath):
        with open(filepath, 'wb') as fh:
            fh.write(self.pack())

    def save_json(self, filepath):
        '''Saves the .msh in JSON format.'''
        data = {
            'info': self.info.get_json(),
            'models': self.models.get_json(),
            'materials': self.materials.get_json(),
            'has_shadowvolume': self.has_shadowvolume,
            'animation': None,
        }
        with open(filepath, 'wb') as fh:
            fh.write(json.dumps(data, indent=4, separators=(',', ': ')))
        return True

    def save_segmented_json(self, folder, name=None):
        # If no name argument was passed assume that a full path was passed.
        if not name:
            folder, name = os.path.dirname(folder), os.path.basename(folder)
            name = name.split('.')[0]
        if not os.path.isdir(folder):
            os.mkdir(folder)
        with open(os.path.join(folder, name + '.txt'), 'w') as fh:
            fh.write(json.dumps({'has_shadowvolume': self.has_shadowvolume}))
        with open(os.path.join(folder, name + ' nfo.txt'), 'w') as fh:
            fh.write(json.dumps(self.info.get_json(), indent=4, separators=(',', ': ')))
        for model in self.models:
            model.save_segmented_json(folder, name)
        for material in self.materials:
            with open(os.path.join(folder, '{0} mtl {1}.txt'.format(name, material.name)), 'wb') as fh:
                fh.write(json.dumps(material.get_json(), indent=4, separators=(',', ': ')))

    @classmethod
    def load_segmented_json(cls, folder, name):
        model_start = '{0} mdl '.format(name)
        material_start = '{0} mtl '.format(name)
        msh = cls()
        info_data = ''
        with open(os.path.join(folder, '{0}.txt'.format(name)), 'r') as fh:
            msh.has_shadowvolume = json.loads(fh.read())['has_shadowvolume']
        with open(os.path.join(folder, '{0} nfo.txt'.format(name)), 'r') as fh:
            info_data = json.loads(fh.read())
        msh.info = SceneInfo.from_json(info_data)
        materials = MaterialCollection(msh)
        models = ModelCollection(msh)
        for filename in os.listdir(folder):
            if filename.startswith(model_start) and (not ' seg ' in filename):
                models.add(Model.load_segmented_json(folder, filename.split('.')[0]))
            elif filename.startswith(material_start):
                with open(os.path.join(folder, filename), 'r') as fh:
                    materials.add(Material.from_json(json.loads(fh.read())))
        msh.models = models
        # Re-order models so that parents appear before their children.
        models_map = {}
        models = []
        for model in msh.models:
            if model.parent_name:
                if not models_map.get(model.parent_name, None):
                    models_map[model.parent_name] = [model]
                else:
                    models_map[model.parent_name].append(model)
            else:
                models.append(model)
        new_models = []
        for model in models:
            new_models.extend(msh.get_children_ordered(model, models_map))
        msh.models.replace(new_models)
        msh.materials = materials
        msh.animation = Animation(None, 'empty')
        msh.set_indices()
        return msh

    def get_children_ordered(self, model, children_map):
        models = []
        models.append(model)
        children = children_map.get(model.name, [])
        for child in children:
            models.extend(self.get_children_ordered(child, children_map))
        return models

    @classmethod
    def load_json(cls, filepath):
        data = ''
        with open(filepath, 'rb') as fh:
            data = fh.read()
        data = json.loads(data)
        msh = cls()
        msh.info = SceneInfo.from_json(data['info'], msh)
        msh.models = ModelCollection.from_json(data['models'], msh)
        msh.materials = MaterialCollection.from_json(data['materials'], msh)
        msh.has_shadowvolume = data['has_shadowvolume']
        msh.animation = Animation(None, 'empty')
        msh.set_indices()
        return msh

    def set_indices(self):
        '''Set material and model indices (ie after json load).'''
        for index, material in enumerate(self.materials):
            material.index = index
        for index, model in enumerate(self.models):
            model.index = index
            for seg in model.segments:
                seg.material = self.get_mat_by_name(seg.mat_name)

    def get_mat_by_name(self, name):
        '''Get Material object by name.'''
        dct = self.materials.get_matname_dict()
        return dct[name]

    def get_mat_by_index(self, index):
        '''Get Material object by index into the colection.'''
        return self.materials[index]

    def pack_CL1L(self):
        data = ['CL1L']
        data.append(struct.pack('<L', 0))
        return ''.join(data)

    def pack(self):
        '''Packs data to .msh file structure and returns the data as a string.'''
        data = ['HEDR',
                'hedr_len']
        # First pack the MSH2 header with all its children chunks.
        msh2_data = ['MSH2', 'len']
        msh2_data.append(self.info.pack())
        msh2_data.append(self.materials.pack())
        msh2_data.append(self.models.pack())
        #msh2_data[1] = struct.pack('<L', len(msh2_data[2]) + len(msh2_data[3]) + len(msh2_data[4]))
        msh2_data[1] = struct.pack('<L', self.sum_seq(msh2_data, 2))
        # Finished MSH2.
        data.append(''.join(msh2_data))
        # HEDR only has MSH2 and the animation chunks as children(and sometimes SHVO).
        # We don't pack SHVO here so on to animation chunks.
        data.append(self.animation.pack())
        data.append(self.pack_CL1L())
        # sum length of msh2 data + length of animation chunks.
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)

    def repack(self):
        '''Will use stored binary data of cloth and shadow chunks instead
        of recalculating it(not possible at the moment).'''
        data = ['HEDR',
                'hedr_len']
        # First pack the MSH2 header with all its children chunks.
        msh2_data = ['MSH2', 'len']
        msh2_data.append(self.info.pack())
        msh2_data.append(self.materials.pack())
        msh2_data.append(self.models.repack())
        #msh2_data[1] = struct.pack('<L', len(msh2_data[2]) + len(msh2_data[3]) + len(msh2_data[4]))
        msh2_data[1] = struct.pack('<L', self.sum_seq(msh2_data, 2))
        # Finished MSH2.
        data.append(''.join(msh2_data))
        # HEDR only has MSH2 and the animation chunks as children(and sometimes SHVO).
        # We don't pack SHVO here so on to animation chunks.
        if self.animation:
            data.append(self.animation.pack())
        data.append(self.pack_CL1L())
        # sum length of msh2 data + length of animation chunks.
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)


class SceneInfo(Packer):
    def __init__(self, msh=None):
        # Reference to Msh.
        if msh:
            self.msh = msh
        else:
            self.msh = None
        self.name = ''
        self.classname = 'SceneInfo'
        self.frame_range = 0, 100
        self.fps = 29.97
        self.scale = 1.0, 1.0, 1.0
        self.bbox = BBox()

    def dump(self, fileh=None):
        '''Dump information to open filehandler fileh.'''
        if fileh:
            fileh.write('--- SceneInfo ---\n')
            fileh.write('\tSceneName:  {0}\n'.format(self.name))
            fileh.write('\tFrameRange: {0}-{1}\n'.format(*self.frame_range))
            fileh.write('\tFPS:        {0}\n'.format(self.fps))

    def get_json(self):
        data = {
            'name': self.name,
            'frame_range': self.frame_range,
            'fps': self.fps,
            'scale': self.scale,
            'bbox': self.bbox.get_json()
        }
        return data

    @staticmethod
    def from_json(data, msh=None):
        info = SceneInfo()
        info.msh = msh
        info.name = data['name']
        info.frame_range = data['frame_range']
        info.fps = data['fps']
        info.scale = data['scale']
        info.bbox = BBox.from_json(data['bbox'])
        return info

    def pack(self):
        '''Packs the scene information data.'''
        data = ['SINF']
        data.append('size_ind')
        data.append(self.pack_NAME())
        data.append(self.pack_FRAM())
        data.append(self.bbox.pack())
        data[1] = struct.pack('<L', len(data[2]) + len(data[3]) + len(data[4]))
        return ''.join(data)

    def pack_NAME(self):
        '''Packs the scene name.'''
        return self.pack_string_chunk('NAME', self.name)

    def pack_FRAM(self):
        '''Packs frame range and FPS into the FRAM chunk.'''
        data = ['FRAM']
        data.append(struct.pack('<L', 12))
        data.append(struct.pack('<L', self.frame_range[0]))
        data.append(struct.pack('<L', self.frame_range[1]))
        data.append(struct.pack('<f', self.fps))
        return ''.join(data)


class Material(Packer):
    # name: string
    # index: int
    # tex_0: string.tga
    # tex_1: string.tga
    # tex_2: string.tga
    # tex_3: string.tga
    # attr_0: int(0-255)
    # attr_1: int(0-255)
    # attr_2: int(0-255)
    # attr_3: int(0-255)
    # diff_color: (red, green, blue, alpha) floats
    # ambt_color: (red, green, blue, alpha) floats
    # spec_color: (red, green, blue, alpha) floats
    # gloss: float
    def __init__(self, coll=None):
        # Reference to MaterialCollection
        if coll:
            self.collection = coll
        else:
            self.collection = None
        self.name = ''
        self.classname = 'Material'
        self.index = 0
        self.tex0 = None
        self.tex1 = None
        self.tex2 = None
        self.tex3 = None
        self.flags = [['specular', False, 128],
                      ['additive', False, 64],
                      ['perpixel', False, 32],
                      ['hard', False, 16],
                      ['double', False, 8],
                      ['single', False, 4],
                      ['glow', False, 2],
                      ['emissive', False, 1]]
        self.render_type = 0
        self.data0 = 0
        self.data1 = 0
        self.diff_color = Color()
        self.ambt_color = Color()
        self.spec_color = Color()
        self.gloss = 70.0

    def dump(self, fh):
        '''Dump information to open filehandler fileh.'''
        fh.write('\t--- Material ---\n')
        fh.write('\t\tName:  {0}\n'.format(self.name))
        fh.write('\t\tTex0:  {0}\n'.format(self.tex0))
        fh.write('\t\tTex1:  {0}\n'.format(self.tex1))
        fh.write('\t\tTex2:  {0}\n'.format(self.tex2))
        fh.write('\t\tTex3:  {0}\n'.format(self.tex3))
        fh.write('\t\tFlags\n')
        for flag in self.flags:
            fh.write('\t\t\t{0}: {1}\n'.format(flag[0], flag[1]))
        fh.write('\n')
        fh.write('\t\tRenderType: {0}\n'.format(self.render_type))
        fh.write('\t\tData0:      {0}\n'.format(self.data0))
        fh.write('\t\tData1:      {0}\n'.format(self.data1))
        fh.write('\t\tDiffuse:    {0}\n'.format(self.diff_color))
        fh.write('\t\tSpecular:   {0}\n'.format(self.spec_color))
        fh.write('\t\tAmbient:    {0}\n'.format(self.ambt_color))
        fh.write('\t\tGloss:      {0}\n'.format(self.gloss))

    def get_json(self):
        data = {
            'name': self.name,
            'index': self.index,
            'tex0': self.tex0,
            'tex1': self.tex1,
            'tex2': self.tex2,
            'tex3': self.tex3,
            'flags': self.flags,
            'render_type': self.render_type,
            'data0': self.data0,
            'data1': self.data1,
            'diffuse': self.diff_color.get_json(),
            'specular': self.spec_color.get_json(),
            'ambient': self.ambt_color.get_json(),
            'gloss': self.gloss,
        }
        return data

    @staticmethod
    def from_json(data, collection=None):
        material = Material()
        material.collection = collection
        material.name = data['name']
        material.index = data['index']
        material.tex0 = data['tex0']
        material.tex1 = data['tex1']
        material.tex2 = data['tex2']
        material.tex3 = data['tex3']
        material.flags = data['flags']
        material.render_type = data['render_type']
        material.data0 = data['data0']
        material.data1 = data['data1']
        material.diff_color = Color.from_json(data['diffuse'])
        material.spec_color = Color.from_json(data['specular'])
        material.ambt_color = Color.from_json(data['ambient'])
        material.gloss = data['gloss']
        return material

    @property
    def ATRB(self):
        '''Sum ATRB byte value.'''
        val = 0
        for flag in self.flags:
            if flag[1]:
                val += flag[2]
        return val

    def pack(self):
        '''Packs the material into a MATD chunk.'''
        data = ['MATD']
        data.append('size_indicator')
        data.append(self.pack_NAME())
        data.append(self.pack_DATA())
        data.append(self.pack_ATRB())
        data.append(self.pack_textures())
        data[1] = struct.pack('<L', len(data[2]) + len(data[3]) + len(data[4]) + len(data[5]))
        return ''.join(data)

    def flags_from_int(self, val):
        '''Unpacks an int indicating the material flags into the
        single flags.'''
        # Decodes an int into flags.
        place0 = val
        flags = [('specular', True, 128),
                 ('additive', True, 64),
                 ('perpixel', True, 32),
                 ('hard', True, 16),
                 ('double', True, 8),
                 ('single', True, 4),
                 ('glow', True, 2),
                 ('emissive', True, 1)]
        new = place0
        for index, flag in enumerate(flags):
            new -= flag[2]
            if new < 0:
                flags[index] = flag[0], False, flag[2]
                new += flag[2]
        return flags

    def pack_NAME(self):
        '''Packs the materials name.'''
        return self.pack_string_chunk('NAME', self.name)

    def pack_DATA(self):
        '''Packs the material's shader/color data.'''
        data = ['DATA']
        data.append(struct.pack('<L', 52))
        data.append(self.diff_color.pack('f'))
        data.append(self.spec_color.pack('f'))
        data.append(self.ambt_color.pack('f'))
        data.append(struct.pack('<f', self.gloss))
        return ''.join(data)

    def pack_ATRB(self):
        '''Packs the material render attributes.'''
        data = ['ATRB']
        data.append(struct.pack('<L', 4))
        data.append(struct.pack('<B', self.ATRB))
        data.append(struct.pack('<B', self.render_type))
        data.append(struct.pack('<B', self.data0))
        data.append(struct.pack('<B', self.data1))
        return ''.join(data)

    def pack_textures(self):
        '''Packs up to 4 textures in TX0D/TX1D/TX2D/TX3D chunks.'''
        data = []
        if self.tex0:
            data.append(self.pack_string_chunk('TX0D', self.tex0))
        if self.tex1:
            data.append(self.pack_string_chunk('TX1D', self.tex1))
        if self.tex2:
            data.append(self.pack_string_chunk('TX2D', self.tex2))
        if self.tex3:
            data.append(self.pack_string_chunk('TX3D', self.tex3))
        return ''.join(data)


class MaterialCollection(Packer):
    def __init__(self, msh=None, materials=None):
        # Reference to Msh.
        if msh:
            self.msh = msh
        else:
            self.msh = None
        self.classname = 'MaterialCollection'
        if materials:
            self.materials = materials
        else:
            self.materials = []

    def dump(self, fh):
        '''Dump information to open filehandler fileh.'''
        fh.write('--- MaterialCollection ---\n')
        fh.write('\tNumMaterials: {0}\n'.format(len(self.materials)))
        for mat in self.materials:
            mat.dump(fh)

    def get_json(self):
        data = {
            'materials': [mat.get_json() for mat in self.materials],
        }
        return data

    @staticmethod
    def from_json(data, msh=None):
        coll = MaterialCollection()
        coll.msh = msh
        for material_data in data['materials']:
            coll.materials.append(Material.from_json(material_data))
        return coll

    def add(self, material):
        '''Add Material to the collection and set
        collection attribute.'''
        material.collection = self
        self.materials.append(material)

    def remove(self, index):
        '''Remove material at index index.'''
        del self.materials[index]

    def replace(self, materials):
        '''Replace internal materials list.'''
        self.materials = materials

    def get_matname_dict(self):
        '''Returns dict of 'materialname': material pairs.'''
        matnamedict = {}
        for mat in self.materials:
            matnamedict[mat.name] = mat
        return matnamedict

    def assign_indices(self):
        '''Assigns index attribute for every material.'''
        for index, mat in enumerate(self.materials):
            mat.index = index

    def __str__(self):
        return str(self.materials)

    def __repr__(self):
        return str(self.materials)

    def __getitem__(self, key):
        return self.materials[key]

    def __len__(self):
        return len(self.materials)

    def pack(self):
        '''Packs the material list + materials.'''
        data = ['MATL', 'size']
        data.append(struct.pack('<L', len(self.materials)))
        for material in self.materials:
            data.append(material.pack())
        data[1] = struct.pack('<L', self.sum_seq(data, 3) + 4)
        return ''.join(data)


class Model(Packer):
    collprim_by_index = {0: 'Sphere',
                         1: 'Sphere',
                         2: 'Cylinder',
                         4: 'Cube'}
    collprim_by_name = {'Sphere': 0,
                        'Cylinder': 2,
                        'Cube': 4}

    def __init__(self, collection=None):
        # Ref to ModelCollection.
        if collection:
            self.collection = collection
        else:
            self.collection = None
        self.name = 'model'
        self.classname = 'Model'
        self.parent_name = None
        self.index = 0
        self.model_type = 'geostatic'
        self.vis = 0
        self.segments = SegmentCollection(self)
        self.collprim = False
        self.cloth_collprim = False
        self.primitive = 4, 0.0, 0.0, 0.0
        self.deformers = []
        self.deformer_indices = []
        self.bbox = BBox()
        self.transform = Transform()
        self.bone = None
        self.msh = None

    def get_json(self):
        data = {
            'name': self.name,
            'parent': self.parent_name,
            'model_type': self.model_type,
            'visible': not self.vis,  # vis == hidden
            'segments': self.segments.get_json(),
            'collprim': self.collprim,
            'primitive': self.primitive,
            'num_deformers': len(self.deformers),
            'deformers': self.deformers,
            'bbox': self.bbox.get_json(),
            'transform': self.transform.get_json(),
        }
        return data

    def save_segmented_json(self, folder, name):
        data = self.get_json()
        del data['segments']
        with open(os.path.join(folder, '{0} mdl {1}.txt'.format(name, self.name)), 'w') as fh:
            fh.write(json.dumps(data, indent=4, separators=(',', ': ')))
        for index, segment in enumerate(self.segments):
            with open(os.path.join(folder, '{0} mdl {1} seg {2:0>3}.txt'.format(name, self.name, index)), 'w') as fh:
                fh.write(json.dumps(segment.get_json(), indent=4, separators=(',', ': ')))

    @classmethod
    def load_segmented_json(cls, folder, name):
        print 'LOADING SEGMENTED MODEL {0} {1}'.format(folder, name)
        with open(os.path.join(folder, '{0}.txt'.format(name)), 'r') as fh:
            model = Model.from_json(json.loads(fh.read()))
        seg_start = '{0} seg '.format(name)
        segments = SegmentCollection(model)
        for filename in os.listdir(folder):
            if filename.startswith(seg_start):
                with open(os.path.join(folder, filename), 'r') as fh:
                    data = json.loads(fh.read())
                if data['type'] == 'SegmentGeometry':
                    segments.add(SegmentGeometry.from_json(data))
                elif data['type'] == 'ClothGeometry':
                    segments.add(ClothGeometry.from_json(data))
                elif data['type'] == 'ShadowGeometry':
                    segments.add(ShadowGeometry.from_json(data))
        model.segments = segments
        return model

    @staticmethod
    def from_json(data, collection=None):
        model = Model()
        model.collection = collection
        model.name = data['name']
        model.parent_name = data['parent']
        model.model_type = data['model_type']
        model.vis = data.get('visible', False)
        model.vis = data.get('vis', model.vis)  # Older format used that.
        # In case this is loaded from a segmented json.
        if data.get('segments', None):
            model.segments = SegmentCollection.from_json(data['segments'], model)
        model.collprim = data['collprim']
        model.primitive = data['primitive']
        model.deformers = data['deformers']
        model.bbox = BBox.from_json(data['bbox'])
        model.transform = Transform.from_json(data['transform'])
        return model

    def get_collprim_name(self):
        return self.collprim_by_index[self.primitive[0]]

    def get_collprim_index(self, name):
        return self.collprim_by_name[name]

    def dump(self, fh):
        '''Dump information to open filehandler fileh.'''
        fh.write('\t--- Model ---\n')
        fh.write('\t\tName:    {0}\n'.format(self.name))
        fh.write('\t\tParent:  {0}\n'.format(self.parent_name))
        fh.write('\t\tType:    {0}\n'.format(self.model_type))
        fh.write('\t\tVisible: {0}\n'.format(self.vis))
        fh.write('\t\tPos:     {0}, {1}, {2}\n'.format(*self.transform.translation))
        fh.write('\t\tRot:     {0}, {1}, {2}, {3}\n'.format(*self.transform.rotation))
        fh.write('\t\tScl:     {0}, {1}, {2}\n'.format(*self.transform.scale))
        if self.collprim:
            fh.write('\t\tCollprim: {0}, {1}, {2}, {3}\n'.format(*self.primitive))
        if 'geo' in self.model_type or self.model_type == 'cloth':
            self.segments.dump(fh)
        if self.deformers:
            fh.write('\t\tDeformers:\n')
            for deform in self.deformers:
                fh.write('\t\t\t{0}\n'.format(deform))

    def set_deformers_from_indices(self):
        '''Sets deformers attribute to actual model names.'''
        try:
            for ind in self.deformer_indices:
                self.deformers.append(self.collection[ind - 1].name)
        except IndexError:
            print 'Index({0})'.format(ind)
            raise MSH2Error('Check C:\dump.dump!')

    def pack(self):
        '''Packs the MODL chunk. This should be used to retrieve the model in packed form.'''
        data = ['MODL', 'sizeind']
        data.append(self.pack_MTYP())
        data.append(self.pack_MNDX())
        data.append(self.pack_NAME())
        if self.parent_name:
            data.append(self.pack_PRNT())
        data.append(self.pack_FLGS())
        data.append(self.transform.pack())
        if 'geo' in self.model_type or self.model_type == 'cloth':
            data.append(self.pack_GEOM())
            if self.collprim:
                data.append(self.pack_SWCI())
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)

    def pack_MTYP(self):
        '''Packs the model type chunk.'''
        return self.pack_long_chunk('MTYP', MODEL_TYPES[self.model_type])

    def pack_MNDX(self):
        '''Packs the model index chunk.'''
        return self.pack_long_chunk('MNDX', self.index)

    def pack_NAME(self):
        '''Packs the model's name.'''
        return self.pack_string_chunk('NAME', self.name)

    def pack_PRNT(self):
        '''Packs the model's parent's name.'''
        return self.pack_string_chunk('PRNT', self.parent_name)

    def pack_FLGS(self):
        '''Packs the visibility.'''
        return self.pack_long_chunk('FLGS', self.vis)

    def pack_GEOM(self):
        data = ['GEOM']
        data.append('size_indic')
        data.append(self.bbox.pack())
        data.append(self.segments.pack())
        if self.deformers:
            data.append(self.pack_ENVL())
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)

    def pack_ENVL(self):
        data = ['ENVL']
        data.append(struct.pack('<L', len(self.deformers) * 4 + 4))
        data.append(struct.pack('<L', len(self.deformers)))
        for deformer in self.deformers:
            index = self.collection.get_index(deformer)
            data.append(struct.pack('<L', index))
        return ''.join(data)

    def pack_SWCI(self):
        '''Packs the collision primitive chunk.'''
        data = ['SWCI']
        data.append(struct.pack('<L', 16))
        data.append(struct.pack('<Lfff', *self.primitive))
        return ''.join(data)

    def repack(self):
        '''Repacks the MODL chunk. This should be used to retrieve the model in packed form.'''
        data = ['MODL', 'sizeind']
        data.append(self.pack_MTYP())
        data.append(self.pack_MNDX())
        data.append(self.pack_NAME())
        if self.parent_name:
            data.append(self.pack_PRNT())
        data.append(self.pack_FLGS())
        data.append(self.transform.pack())
        if 'geo' in self.model_type or self.model_type == 'cloth':
            data.append(self.repack_GEOM())
            if self.collprim:
                data.append(self.pack_SWCI())
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)

    def repack_GEOM(self):
        data = ['GEOM']
        data.append('size_indic')
        data.append(self.bbox.pack())
        data.append(self.segments.repack())
        if self.deformers:
            data.append(self.pack_ENVL())
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)


class ModelCollection(object):
    def __init__(self, msh=None, models=None):
        # Ref to Msh.
        if msh:
            self.msh = msh
        else:
            self.msh = None
        self.classname = 'ModelCollection'
        if models:
            self.models = models
        else:
            self.models = []
        self.msh = None

    def get_json(self):
        data = {
            'models': [m.get_json() for m in self.models]
        }
        return data

    @staticmethod
    def from_json(data, msh=None):
        coll = ModelCollection()
        coll.msh = msh
        for model_data in data['models']:
            coll.models.append(Model.from_json(model_data, coll))
        return coll

    def dump(self, fh):
        '''Dump information to open filehandler fh.'''
        fh.write('--- ModelCollection ---\n')
        fh.write('\tNumModels: {0}\n'.format(len(self.models)))
        for model in self.models:
            model.dump(fh)

    def add(self, model):
        '''Add Model object and set its collection
        attribute.'''
        model.collection = self
        self.models.append(model)

    def remove(self, index):
        del self.models[index]

    def remove_multi(self, models):
        '''Compares names between internal list and
        models. If name of internal Model equals one in
        models, remove the Model.'''
        for index, model in enumerate(self.models):
            if model.name in models:
                del self.models[index]

    def replace(self, new_models):
        '''Replace internal model list with new_models.'''
        self.models = new_models

    def assign_indices(self):
        '''Assign index attribute for every Model.'''
        for index, model in enumerate(self.models):
            model.index = index + 1

    def assign_parents(self):
        '''Assign collection attribute for every Model.'''
        for model in self.models:
            model.collection = self

    def assign_cloth_collisions(self):
        '''Assign collision data to every cloth that has collisions referenced.'''
        cloth_collision_primitives = {}
        for model in self.models:
            if model.cloth_collprim:
                cloth_collision_primitives[model.name] = model

        for model in self.models:
            for segment in model.segments:
                if isinstance(segment, ClothGeometry):
                    for collision in segment.collisions:
                        collision.primitive_type = cloth_collision_primitives[collision.name].primitive[0]
                        collision.primitive_data = cloth_collision_primitives[collision.name].primitive[1:]

    def get_index(self, modelname):
        '''Get model.index for model with name modelname.'''
        for model in self.models:
            if model.name == modelname:
                logging.debug('ModelCollection.get_index: {0} - {1}'.format(model.name, model.index))
                return model.index
        return 0

    def by_name(self, name):
        '''Get model by name.'''
        for model in self.models:
            if model.name == name:
                return model

    def get_names_list(self):
        '''Get list of model names.'''
        return [mdl.name for mdl in self.models]

    def __str__(self):
        return str(self.models)

    def __repr__(self):
        return str(self.models)

    def __getitem__(self, key):
        return self.models[key]

    def __len__(self):
        return len(self.models)

    def pack(self):
        data = [model.pack() for model in self.models]
        return ''.join(data)

    def repack(self):
        data = [model.repack() for model in self.models]
        return ''.join(data)


class SegmentCollection(object):
    def __init__(self, model=None, segments=None):
        # Reference to Model.
        if model:
            self.model = model
        else:
            self.model = None
        self.classname = 'SegmentCollection'
        if segments:
            self.segments = segments
        else:
            self.segments = []
        self.msh = None

    def get_json(self):
        data = {
            'segments': [seg.get_json() for seg in self.segments],
        }
        return data

    @staticmethod
    def from_json(data, model=None):
        coll = SegmentCollection()
        coll.model = model
        for segment_data in data['segments']:
            if segment_data['type'] == 'SegmentGeometry':
                coll.segments.append(SegmentGeometry.from_json(segment_data, coll))
            elif segment_data['type'] == 'ClothGeometry':
                coll.segments.append(ClothGeometry.from_json(segment_data, coll))
            elif segment_data['type'] == 'ShadowGeometry':
                coll.segments.append(ShadowGeometry.from_json(segment_data, coll))
        return coll

    def dump(self, fh):
        '''Dump information to open filehandler fileh.'''
        fh.write('\t\t--- SegmentCollection ---\n')
        for seg in self.segments:
            seg.dump(fh)

    def num_vertices(self):
        numv = 0
        for segm in self.segments:
            numv += len(segm.vertices)
        return numv

    def add(self, segment):
        '''Adds SegmentGeometry, ClothGeometry or ShadowGeometry
        to the collection and sets the collection attribute.'''
        segment.collection = self
        self.segments.append(segment)

    def remove(self, index):
        '''Removes Geometry at index index.'''
        del self.segments[index]

    def split(self, seg_index, poly_mat_inds, mat_names):
        '''Splits the segment with index == seg_index.
        poly_mat_inds is a list where the index represents
        the index of the face/polygon and the content of the
        list item represents the material index.
        mat_names is a list of material names.
        This function splits the segment into multiple
        segments(one per material). The result segments
        will be used as the .segments of this SegmentCollection.'''
        polies_per_material = self._polies_per_material(poly_mat_inds)
        # Segment to split.
        segm = self.segments[seg_index]
        segments = []
        # Loop through materials.
        for mat_index, mat_poly_indices in enumerate(polies_per_material):
            if not mat_poly_indices:
                continue
            seg = SegmentGeometry(self)
            facecoll = FaceCollection(seg)
            vertcoll = VertexCollection(seg)
            vertcoll.set_flags_from_vertcoll(segm.vertices)
            # Loop through face indices.
            for local_face_index, face_index in enumerate(mat_poly_indices):
                master_face = segm.faces[face_index]
                new_face = Face()
                for vert_index in master_face.vertices:
                    # Add the vertex. As the vertex now holds UV, weights etc
                    # its not necessary anymore to do all the checking if
                    # the UV etc lists should be split, too.
                    vertcoll.add(segm.vertices[vert_index])
                    # Add last item in vertex collection to face.
                    new_face.add(len(vertcoll) - 1)
                facecoll.add(new_face)
            seg.vertices = vertcoll
            seg.faces = facecoll
            seg.mat_name = mat_names[mat_index]
            seg.mat = self.msh.get_mat_by_name(segm.mat_name)
            segments.append(seg)
        self.segment = []
        self.segments = segments

    def assign_materials(self, material_coll):
        '''Assign material object from material name.'''
        mat_name_dict = material_coll.get_matname_dict()
        for segment in self.segments:
            segment.material = mat_name_dict[segment.mat_name]

    def _polies_per_material(self, poly_inds):
        '''Creates a list where each item represents a material and holds
        all polygon indices mapped to that material.'''
        largest_index = self._mat_largest_ind(poly_inds)
        # Create sub-lists for every material.
        list_ = [[] for n in xrange(largest_index + 1)]
        for index, el in enumerate(poly_inds):
            # Now add the polygon indices to the according mat list.
            list_[el].append(index)
        return list_

    def _mat_largest_ind(self, inds):
        '''Largest material index. Equals number of materials.'''
        int_ = 0
        for el in inds:
            if el > int_:
                int_ = el
        return int_

    def __str__(self):
        return str(self.segments)

    def __repr__(self):
        return str(self.segments)

    def __getitem__(self, key):
        return self.segments[key]

    def __len__(self):
        return len(self.segments)

    def pack(self):
        data = []
        for segment in self.segments:
            data.append(segment.pack())
        return ''.join(data)

    def repack(self):
        data = [segment.repack() for segment in self.segments]
        return ''.join(data)


class SegmentGeometry(Packer):
    # mat_name: string
    # mat_index: int
    # vert_list: list (Vertex)
    # face_list: list (Face)
    def __init__(self, collection=None):
        #Reference to SegmentCollection.
        if collection:
            self.collection = collection
        else:
            self.collection = None
        self.classname = 'SegmentGeometry'
        self.mat_name = None
        self.material = None
        self.vertices = None
        self.faces = None
        self.msh = None
        self.index_map = None

    def get_json(self):
        data = {
            'type': self.classname,
            'material': self.material.name.encode('utf-8'),
            'num_vertices': len(self.vertices),
            'vertices': self.vertices.get_json(),
            'num_faces': len(self.faces),
            'faces': self.faces.get_json(),
        }
        return data

    @staticmethod
    def from_json(data, collection=None):
        geo = SegmentGeometry()
        geo.collection = collection
        geo.mat_name = data['material'].encode('utf-8')
        geo.vertices = VertexCollection.from_json(data['vertices'], geo)
        geo.faces = FaceCollection.from_json(data['faces'], geo)
        return geo

    def clear_doubles(self):
        '''Clears Vertices appearing more than once.'''
        self.index_map = dict()
        new_vertices = []
        len_new_verts = 0
        for index, vert in enumerate(self.vertices):
            index_original = None
            try:
                index_original = new_vertices.index(vert)
                # print 'Original: {0}; Double: {1}'.format(new_vertices[index_original].normal, vert.normal)
            except ValueError:
                #print 'ValueError', vert
                pass
            #print index
            if index_original:
                # Insert into indices map.
                self.index_map[index] = index_original
            else:
                new_vertices.append(vert)
                self.index_map[index] = len_new_verts
                len_new_verts += 1
        self.vertices.vertices = new_vertices

    def dump(self, fh):
        '''Dump information to open filehandler fileh.'''
        fh.write('\t\t\t--- SegmentGeometry ---\n')
        fh.write('\t\t\t\tMaterial:    {0}\n'.format(self.material))
        fh.write('\t\t\t\tVertices:    {0}\n'.format(len(self.vertices)))
        fh.write('\t\t\t\tFaces:       {0}\n'.format(len(self.faces or '')))
        fh.write('\t\t\t\tUVed:        {0}\n'.format(self.vertices.uved))
        fh.write('\t\t\t\tColored:     {0}\n'.format(self.vertices.colored))
        fh.write('\t\t\t\tWeighted:    {0}\n'.format(self.vertices.weighted))
        fh.write(str(self.index_map))

    def pack_MATI(self):
        return self.pack_long_chunk('MATI', self.material.index)

    def pack(self):
        '''Packs the SEGM chunk. This should be used to retrieve the segment in packed form.'''
        data = ['SEGM']
        data.append('size')
        data.append(self.pack_MATI())
        data.append(self.vertices.pack())
        data.append(self.faces.pack())
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)

    def repack(self):
        return self.pack()


class ShadowGeometry(Packer):
    def __init__(self, collection=None):
        if collection:
            self.collection = collection
        else:
            self.collection = None
        self.classname = 'ShadowGeometry'
        self.data = ''
        self.positions = []
        self.edges = []

    def get_json(self):
        data = {
            'type': self.classname,
            'num_positions': len(self.positions),
            'positions': self.positions,
            'num_edges': len(self.edges),
            'edges': self.edges,
        }
        return data

    @staticmethod
    def from_json(data, collection=None):
        geo = ShadowGeometry()
        geo.collection = collection
        geo.positions = data['positions']
        geo.edges = data['edges']
        return geo

    def dump(self, fh):
        '''Dump information to open filehandler fileh.'''
        fh.write('\t\t\t--- ShadowGeometry ---\n')
        fh.write('\t\t\t\tNo data available.\n')

    def repack(self):
        data = ['SHDW', 'size', self.data]
        data[1] = struct.pack('<L', len(self.data))
        return ''.join(data)

    def pack(self):
        data = ['SHDW', 'size']
        data.append(struct.pack('<L', len(self.positions)))
        for pos in self.positions:
            data.append(struct.pack('<fff', *pos))
        data.append(struct.pack('<L', len(self.edges)))
        for edge in self.edges:
            data.append(struct.pack('<HHHH', *edge))
        data[1] = struct.pack('<L', 4 + 4 + 6 * len(self.edges) + 12 * len(self.positions))
        return ''.join(data)


class ClothCollision(Packer):
    def __init__(self, cloth_geo=None):
        self.cloth = cloth_geo
        self.name = ''
        self.parent = ''
        # 0: Sphere, 1: Cylinder
        self.primitive_type = 0
        self.primitive_data = 4, 4, 4

    def get_json(self):
        data = {
            'name': self.name,
            'parent': self.parent,
            'primitive_type': self.primitive_type,
            'primitive_data': self.primitive_data,
        }
        return data

    @classmethod
    def from_json(cls, data, cloth=None):
        cc = cls()
        cc.cloth = cloth
        cc.name = data['name']
        cc.parent = data['parent']
        cc.primitive_type = data['primitive_type']
        cc.primitive_data = data['primitive_data']
        return cc

    def pack(self):
        data = [self.name + '\x00',
                self.parent + '\x00',
                struct.pack('<L', self.primitive_type),
                struct.pack('<fff', *self.primitive_data)]
        return ''.join(data)


class ClothGeometry(Packer):
    def __init__(self, collection=None):
        if collection:
            self.collection = collection
        else:
            self.collection = None
        self.classname = 'ClothGeometry'
        self.texture = 'no_texture'
        self.vertices = None
        self.faces = None
        # These are only for repack.
        self.stretch = ''
        self.stretch_constraints = []
        self.cross = ''
        self.cross_constraints = []
        self.bend = ''
        self.bend_constraints = []
        self.collision = ''
        self.collisions = []

    def get_json(self):
        data = {
            'type': self.classname,
            'texture': self.texture,
            'num_vertices': len(self.vertices),
            'vertices': self.vertices.get_json(),
            'num_faces': len(self.faces),
            'faces': self.faces.get_json(),
            'stretch': self.stretch_constraints,
            'cross': self.cross_constraints,
            'bend': self.bend_constraints,
            'collisions': [c.get_json() for c in self.collisions],
        }
        return data

    @staticmethod
    def from_json(data, collection=None):
        geo = ClothGeometry()
        geo.collection = collection
        geo.vertices = ClothVertexCollection.from_json(data['vertices'], geo)
        geo.faces = FaceCollection.from_json(data['faces'], geo)
        geo.stretch_constraints = data['stretch']
        geo.cross_constraints = data['cross']
        geo.bend_constraints = data['bend']
        geo.collisions = [ClothCollision.from_json(collision, geo) for collision in data['collisions']]
        return geo

    def dump(self, fh):
        '''Dump information to open filehandler fileh.'''
        fh.write('\t\t\t--- ClothGeometry ---\n')
        fh.write('\t\t\t\tVertices:    {0}\n'.format(len(self.vertices)))
        fh.write('\t\t\t\tFaces:       {0}\n'.format(len(self.faces)))

    def assign_parents(self):
        '''Assign segment attribute for every collection.'''
        self.vertices.segment = self
        self.faces.segment = self

    def create_constraints(self):
        for face in self.faces:
            last_vertex = face.vertices[-1]
            # Stretch constraints.
            for vert in face.vertices:
                self.stretch_constraints.append((last_vertex, vert))
                last_vertex = vert
            # Cross constraints.
            if len(face.vertices) == 4:
                self.cross_constraints.extend(((face.vertices[0], face.vertices[2]), (face.vertices[1], face.vertices[3])))

        for face in self.faces:
            for face2 in self.faces:
                if face is face2:
                    continue
                shared_vertices = []
                share_map = {}
                not_shared_vertices = []
                for vertex in face2.vertices:
                    # Shares an index.
                    if vertex in face.vertices:
                        shared_vertices.append(vertex)
                    else:
                        not_shared_vertices.append(vertex)
                connections = {}
                for shared_vertex in shared_vertices:
                    connections1 = []
                    for connection_vertex in face.get_connections(shared_vertex):
                        if connection_vertex not in shared_vertices:
                            connections1.append(connection_vertex)
                    connections2 = []
                    for connection_vertex in face2.get_connections(shared_vertex):
                        if connection_vertex not in shared_vertices:
                            connections2.append(connection_vertex)
                    for v1, v2 in zip(connections1, connections2):
                        self.bend_constraints.append((v1, v2))
                continue

    def pack_stretch(self):
        data = ['SPRS', struct.pack('<LL', 4 + 4 * len(self.stretch_constraints), len(self.stretch_constraints))]
        for item in self.stretch_constraints:
            data.append(struct.pack('<HH', *item))
        return ''.join(data)

    def repack_stretch(self):
        data = ['SPRS', 'size']
        # Just append the data we read when this .msh was loaded.
        data.append(self.stretch)
        data[1] = struct.pack('<L', len(self.stretch))
        return ''.join(data)

    def pack_cross(self):
        data = ['CPRS', struct.pack('<LL', 4 + 4 * len(self.cross_constraints), len(self.cross_constraints))]
        for item in self.cross_constraints:
            data.append(struct.pack('<HH', *item))
        return ''.join(data)

    def repack_cross(self):
        data = ['CPRS', 'size']
        data.append(self.cross)
        data[1] = struct.pack('<L', len(self.cross))
        return ''.join(data)

    def pack_bend(self):
        data = ['BPRS', struct.pack('<LL', 4 + 4 * len(self.bend_constraints), len(self.bend_constraints))]
        for item in self.bend_constraints:
            data.append(struct.pack('<HH', *item))
        return ''.join(data)

    def repack_bend(self):
        data = ['BPRS', 'size']
        data.append(self.bend)
        data[1] = struct.pack('<L', len(self.cross))
        return ''.join(data)

    def pack_collision(self):
        data = ['COLL', 'size', struct.pack('<L', len(self.collisions))]
        # Length of size indicator = 4.
        size = 4
        for coll in self.collisions:
            data.append(coll.pack())
            size += len(data[-1])
        # Make the length of the chunk a multiple of 4.
        while size % 4 != 0:
            size += 1
            data.append('\x00')
        data[1] = struct.pack('<L', size)
        return ''.join(data)

    def repack_collision(self):
        data = ['COLL', 'size']
        data.append(self.collision)
        data[1] = struct.pack('<L', len(self.collision))
        return ''.join(data)

    def pack(self):
        data = ['CLTH', 'size']
        if self.texture:
            data.append(self.pack_string_chunk('CTEX', self.texture))
        else:
            data.append(self.pack_string_chunk('CTEX', 'no_texture'))
        data.append(self.vertices.pack_pos())
        data.append(self.vertices.pack_uvs())
        data.append(self.vertices.pack_fixed())
        data.append(self.vertices.pack_weights())
        data.append(self.faces.pack_cloth())
        data.append(self.pack_stretch())
        data.append(self.pack_cross())
        data.append(self.pack_bend())
        data.append(self.pack_collision())
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)

    def repack(self):
        data = ['CLTH', 'size']
        if self.texture:
            data.append(self.pack_string_chunk('CTEX', self.texture))
        else:
            data.append(self.pack_string_chunk('CTEX', 'no_texture'))
        data.append(self.vertices.pack_pos())
        data.append(self.vertices.pack_uvs())
        data.append(self.vertices.pack_fixed())
        data.append(self.vertices.pack_weights())
        data.append(self.faces.pack_cloth())
        data.append(self.repack_stretch())
        data.append(self.repack_cross())
        data.append(self.repack_bend())
        data.append(self.repack_collision())
        data[1] = struct.pack('<L', self.sum_seq(data, 2))
        return ''.join(data)


class Face(object):
    '''Keeps the indices of the vertices forming this face.'''
    # Params:
    #   - vertices: a list of indices forming this face.
    #   - coll: the FaceCollection.
    def __init__(self, vertices=None, coll=None):
        # List of vertex indices(ints).
        if vertices:
            self.vertices = vertices
        else:
            self.vertices = None
        # Reference to the FaceCollection.
        if coll:
            self.collection = coll
        else:
            self.collection = None
        self.classname = 'Face'

    def get_json(self):
        data = {
            'vertices': self.vertices,
        }
        return data

    @staticmethod
    def from_json(data, collection=None):
        face = Face()
        face.collection = collection
        face.vertices = data['vertices']
        return face

    def get_connections(self, vertex):
        index = self.vertices.index(vertex)
        connections = []
        if index - 1 < 0:
            connections.append(self.vertices[-1])
        else:
            connections.append(self.vertices[index - 1])
        if index + 1 == len(self.vertices):
            connections.append(self.vertices[0])
        else:
            connections.append(self.vertices[index + 1])
        return connections

    def replace(self, verts):
        '''Replaces the local vertices list with a new one.'''
        self.vertices = verts

    def reverse_order(self):
        '''Reverses the triangle order. Only works with tris.'''
        self.vertices = self.vertices[0], self.vertices[2], self.vertices[1]

    def add(self, vert_index):
        '''Adds a vertex index to the local vertices.'''
        if not self.vertices:
            self.vertices = [vert_index]
            return
        self.vertices.append(vert_index)

    def i(self, index):
        '''Returns the vertex index at index index of the local vertices.'''
        return self.vertices[index]

    def SIindices(self):
        '''Returns the face in CCW order for XSI importing.'''
        if self.sides == 4:
            return self.i(0), self.i(1), self.i(3), self.i(2)
        else:
            return self.i(0), self.i(1), self.i(2)

    @property
    def sides(self):
        '''Returns the number of sides/vertices this face is constructed of.'''
        return len(self.vertices)

    def pack(self):
        '''Packs the vertex indices for the STRP chunk.'''
        index_map = self.collection.segment.index_map
        if (self.sides == 4) and (index_map is not None):
            return struct.pack('<HHHH', index_map[self.vertices[0]] + 0x8000,
                               index_map[self.vertices[1]] + 0x8000,
                               index_map[self.vertices[2]],
                               index_map[self.vertices[3]])
        elif (self.sides == 3) and (index_map is not None):
            return struct.pack('<HHH', index_map[self.vertices[0]] + 0x8000,
                               index_map[self.vertices[1]] + 0x8000,
                               index_map[self.vertices[2]])
        elif (self.sides == 4) and (index_map is None):
            return struct.pack('<HHHH', self.vertices[0] + 0x8000,
                               self.vertices[1] + 0x8000,
                               self.vertices[2],
                               self.vertices[3])
        elif (self.sides == 3) and (index_map is None):
            return struct.pack('<HHH', self.vertices[0] + 0x8000,
                               self.vertices[1] + 0x8000,
                               self.vertices[2])
        else:
            return ''

    def pack_tris(self):
        '''Packs the vertex indices as tris for the CMSH chunk.'''
        # index_map = self.collection.segment.index_map
        # if (self.sides == 4) and (index_map is not None):
        #     return (struct.pack('<LLL', index_map[self.vertices[0]],
        #             index_map[self.vertices[1]],
        #             index_map[self.vertices[2]]),
        #             struct.pack('<LLL', index_map[self.vertices[0]],
        #                         index_map[self.vertices[2]],
        #                         index_map[self.vertices[3]]))
        # elif (self.sides == 3) and (index_map is not None):
        #     return (struct.pack('<LLL', index_map[self.vertices[0]],
        #                         index_map[self.vertices[1]],
        #                         index_map[self.vertices[2]]),)
        # elif (self.sides == 4) and (index_map is None):
        #     return (struct.pack('<LLL', self.vertices[0],
        #             self.vertices[1],
        #             self.vertices[2]),
        #             struct.pack('<LLL', self.vertices[0],
        #                         self.vertices[2],
        #                         self.vertices[3]))
        # elif (self.sides == 3) and (index_map is None):
        #     return (struct.pack('<LLL', self.vertices[0],
        #                         self.vertices[1],
        #                         self.vertices[2]),)
        # else:
        #     return ()
        if self.sides == 4:
            return (struct.pack('<LLL', self.vertices[0],
                                        self.vertices[1],
                                        self.vertices[2]),
                    struct.pack('<LLL', self.vertices[0],
                                        self.vertices[2],
                                        self.vertices[3]))
        elif self.sides == 3:
            return (struct.pack('<LLL', self.vertices[0],
                                        self.vertices[1],
                                        self.vertices[2]))
        else:
            return ()

    def get_edges(self):
        '''Returns unique edges.'''
        if self.sides == 4:
            return ((self.vertices[0], self.vertices[1]),
                    (self.vertices[1], self.vertices[2]),
                    (self.vertices[2], self.vertices[3]),
                    (self.vertices[3], self.vertices[0]))
        elif self.sides == 3:
            return ((self.vertices[0], self.vertices[1]),
                    (self.vertices[1], self.vertices[2]),
                    (self.vertices[2], self.vertices[3]))
        else:
            return []

    def __repr__(self):
        return 'Face({0})'.format(str(self.vertices))

    def __str__(self):
        return 'Face({0})'.format(str(self.vertices))


class FaceCollection(object):
    def __init__(self, segm=None):
        # List of Face objects.
        self.faces = None
        # Ref to parent(SegmentGeometry).
        if segm:
            self.segment = segm
        else:
            self.segment = None
        self.classname = 'FaceCollection'

    def get_json(self):
        data = {
            'faces': [face.get_json() for face in self.faces],
        }
        return data

    @staticmethod
    def from_json(data, segment=None):
        coll = FaceCollection()
        coll.segment = segment
        coll.faces = [Face.from_json(face_data, coll) for face_data in data['faces']]
        return coll

    def get_faces(self):
        '''Returns faces as vertex indices.'''
        faces = []
        for face in self.faces:
            faces.extend([vertex for vertex in face.vertices])
        return faces

    def de_ngonize(self, only_tris=False):
        '''Makes all n-gons to tris or quads. only_tris defines
        if the algorithm should try to fit quads in, too.'''
        if only_tris:
            return self._triangulate_ngons()
        new_faces = []
        for ndx, face in enumerate(self.faces):
            # If the face has more than 4 sides, cut it into
            # multiple faces. Only 3 and 4 sided faces are
            # supported.
            if face.sides > 4:
                nface = Face(self)
                numtris = face.sides - 2
                numquads = numtris / 2.0
                # 4.0 == int(4.0) but 4.5 != int(4.5).
                # So, if it's possible to cut the current face
                # into multiple quads, do it. Otherwise triangulate
                # it.
                if int(numquads) == numquads:
                    for n in xrange(int(numquads)):
                        nface = Face(self)
                        nface.vertices = face.vertices[n * 2:n * 2 + 4]
                        new_faces.append(nface)
                else:
                    for n in xrange(int(numtris)):
                        # Reverse every 2nd tri so every tri is CCW.
                        if n / 2 != n / 2.0:
                            nface = Face(self)
                            nface.vertices = face.vertices[n:n + 3]
                            nface.reverse_order()
                            new_faces.append(nface)
                            continue
                        nface = Face(self)
                        nface.vertices = face.vertices[n:n + 3]
                        new_faces.append(nface)
            else:
                new_faces.append(face)
        self.faces = new_faces

    def _triangulate_ngons(self):
        '''Triangulates n-gons of every face and sets
        the faces to the newly calculated ones.'''
        new_faces = []
        for ndx, face in enumerate(self.faces):
            if face.sides > 3:
                nface = Face(self)
                numtris = face.sides - 2
                # Just triangulate every face with more than 4 sides.
                for n in xrange(int(numtris)):
                    # Reverse every 2nd tri so every tri is CCW.
                    if n / 2 != n / 2.0:
                            nface = Face(self)
                            nface.vertices = face.vertices[n:n + 3]
                            nface.reverse_order()
                            new_faces.append(nface)
                            continue
                    nface = Face(self)
                    nface.vertices = face.vertices[n:n + 3]
                    new_faces.append(nface)
            else:
                new_faces.append(face)
        self.faces = new_faces

    def add(self, face):
        '''Adds a face to the collection.'''
        face.collection = self
        if not self.faces:
            self.faces = [face]
            return
        self.faces.append(face)

    def pack(self):
        '''Packs vertex indices for every face into
        the STRP chunk.'''
        data = ['STRP', 'size', 'numitems']
        faces = 0
        for face in self.faces:
            faces += face.sides
            if face.sides == 4 or face.sides == 3:
                data.append(face.pack())
        data[1] = struct.pack('<L', faces * 2 + 4)
        data[2] = struct.pack('<L', faces)
        return ''.join(data)

    def pack_cloth(self):
        '''Packs triangles of every face into
        the cloth CMSH chunk.'''
        data = ['CMSH', 'size', 'num']
        num = 0
        for face in self.faces:
            facetris = face.pack_tris()
            num += len(facetris)
            data.extend(facetris)
        data[1] = struct.pack('<L', num * 3 * 4 + 4)
        data[2] = struct.pack('<L', num)
        return ''.join(data)

    def stretch_edges(self):
        '''Gets edges for SPRS cloth chunk.'''
        edges = []
        for face in self.faces:
            face_edges = face.get_edges()
            for edge in face_edges:
                if not edge in edges and not (edge[1], edge[0]) in edges:
                    edges.append(edge)
        for index, edge in enumerate(edges):
            if self.segment.vertices[edge[0]].is_fixed and self.segment.vertices[edge[1]].is_fixed:
                edges.pop(index)
        return edges

    def cross_edges(self):
        '''Gets edges for CPRS cloth chunk.'''
        edges = []
        for face in self.faces:
            if face.sides == 4:
                # Append edges which cross the quad.
                edges.append((face.i(0), face.i(2)))
                edges.append((face.i(1), face.i(3)))
        return edges

    def bend_edges(self):
        '''Get edges for BPRS cloth chunk.'''
        return ()

    def __str__(self):
        return str(self.faces)

    def __repr__(self):
        return str(self.faces)

    def __getitem__(self, key):
        return self.faces[key]

    def __len__(self):
        return len(self.faces)


class Vertex(object):
    def __init__(self, pos=(0, 0, 0), normal=None, coll=None):
        # Reference to parent(VertexCollection).
        if coll:
            self.collection = coll
        else:
            self.collection = None
        self.classname = 'Vertex'
        self.index = 0
        self.x = pos[0]
        self.y = pos[1]
        self.z = pos[2]
        if normal:
            self.nx = normal[0]
            self.ny = normal[1]
            self.nz = normal[2]
        else:
            self.nx = 1.0
            self.ny = 1.0
            self.nz = 1.0
        self.u, self.v = 0.0, 0.0
        self.color = Color()
        self.deformers = ['none', 'none', 'none', 'none']
        self.deformer_indices = [0, 0, 0, 0]
        self.weights = [1.0, 0.0, 0.0, 0.0]

    def get_json(self):
        data = {
            'position': self.pos,
            'uv': self.uv,
            'normal': self.normal,
            'deformers': self.deformers,
            'weights': self.weights,
            'color': self.color.get_json()
        }
        return data

    @staticmethod
    def from_json(data, coll=None):
        vert = Vertex()
        vert.collection = coll
        vert.pos = data['position']
        vert.normal = data['normal']
        vert.uv = data['uv']
        vert.color = Color.from_json(data['color'])
        vert.deformers = data['deformers']
        vert.weights = data['weights']
        return vert

    def dump(self, fh):
        fh.write('\t\tVERTEX\n')
        fh.write('\t\t\tPos: {0:3}, {1:3}, {2:3}\n'.format(*self.pos))
        fh.write('\t\t\tUV:  {0:3}, {1:3}\n'.format(*self.uv))

    def __eq__(self, other):
        if (self.x == other.x) and (self.y == other.y) and (self.z == other.z):
            if (self.u == other.u) and (self.v == other.v):
                if (self.nx == other.nx) and (self.ny == other.ny) and (self.nz == other.nz):
                    return True
        return False

    def __repr__(self):
        return 'Vertex({0}, {1}, {2})'.format(*self.pos)

    @property
    def pos(self):
        return self.x, self.y, self.z

    @pos.setter
    def pos(self, value):
        self.x, self.y, self.z = value

    @property
    def uv(self):
        return self.u, self.v

    @uv.setter
    def uv(self, value):
        self.u, self.v = value

    @property
    def normal(self):
        return self.nx, self.ny, self.nz

    @normal.setter
    def normal(self, value):
        self.nx, self.ny, self.nz = value

    def translate(self, vector3):
        self.x += vector3[0]
        self.y += vector3[1]
        self.z += vector3[2]

    def pack_pos(self):
        return struct.pack('<fff', *self.pos)

    def pack_normal(self):
        return struct.pack('<fff', *self.normal)

    def pack_uvs(self):
        return struct.pack('<ff', *self.uv)

    def pack_weights(self):
        data = []
        for index, weight in itertools.izip(self.deformer_indices, self.weights):
            data.append(struct.pack('<Lf', index, weight))
        return ''.join(data)

    def pack_color(self):
        return self.color.pack('B')


class VertexCollection(object):
    def __init__(self, segm=None):
        # Ref to parent SegmentGeometry.
        if segm:
            self.segment = segm
        else:
            self.segment = None
        self.vertices = []
        self.classname = 'VertexCollection'
        self.colored = False
        self.weighted = False
        self.uved = False

    def get_json(self):
        data = {
            'vertices': [v.get_json() for v in self.vertices],
            'colored': self.colored,
            'weighted': self.weighted,
            'uved': self.uved,
        }
        return data

    @staticmethod
    def from_json(data, segment=None):
        coll = VertexCollection()
        coll.segment = segment
        for vdata in data['vertices']:
            coll.vertices.append(Vertex.from_json(vdata, coll))
        coll.colored = data['colored']
        coll.weighted = data['weighted']
        coll.uved = data['uved']
        return coll

    def dump(self, fh):
        for v in self.vertices:
            v.dump(fh)

    def set_flags_from_vertcoll(self, vertcoll):
        '''Transfers flags from the given VertexCollection vertcoll
        to this one.'''
        self.colored = vertcoll.colored
        self.weighted = vertcoll.weighted
        self.uved = vertcoll.uved

    def get_positions(self):
        '''Yield all positions.'''
        for vertex in self.vertices:
            yield vertex.pos

    def pack_positions(self):
        data = ['POSL']
        data.append(struct.pack('<L', len(self.vertices) * 4 * 3 + 4))
        data.append(struct.pack('<L', len(self.vertices)))
        for vertex in self.vertices:
            data.append(vertex.pack_pos())
        return ''.join(data)

    def get_normals(self):
        '''Yield all normals.'''
        for vertex in self.vertices:
            yield vertex.normal

    def pack_normals(self):
        data = ['NRML']
        data.append(struct.pack('<L', len(self.vertices) * 4 * 3 + 4))
        data.append(struct.pack('<L', len(self.vertices)))
        for vertex in self.vertices:
            data.append(vertex.pack_normal())
        return ''.join(data)

    def get_uvs(self):
        '''Yield all UVs.'''
        for vertex in self.vertices:
            yield vertex.uv

    def get_uv_list(self):
        return [vertex.uv for vertex in self.vertices]

    def pack_uvs(self):
        data = ['UV0L']
        data.append(struct.pack('<L', len(self.vertices) * 4 * 2 + 4))
        data.append(struct.pack('<L', len(self.vertices)))
        for vertex in self.vertices:
            data.append(vertex.pack_uvs())
        return ''.join(data)

    def set_uvs(self, uv_list):
        for uv, vertex in itertools.izip(uv_list, self.vertices):
            vertex.u = uv[0]
            vertex.v = uv[1]

    def get_colors(self):
        '''Yield all color values.'''
        for vertex in self.vertices:
            yield vertex.color.get()

    def set_colors(self, color_list):
        for color, vertex in itertools.izip(color_list, self.vertices):
            vertex.color = color

    def pack_colors(self):
        data = ['CLRL']
        data.append(struct.pack('<L', len(self.vertices) * 4 + 4))
        data.append(struct.pack('<L', len(self.vertices)))
        for vertex in self.vertices:
            data.append(vertex.pack_color())
        return ''.join(data)

    def get_weights(self):
        weights = []
        for vertex in self.vertices:
            weights.append(vertex.deformers[0])
            weights.append(vertex.weights[0])
            weights.append(vertex.deformers[1])
            weights.append(vertex.weights[1])
            weights.append(vertex.deformers[2])
            weights.append(vertex.weights[2])
            weights.append(vertex.deformers[3])
            weights.append(vertex.weights[3])
        return weights

    def set_weights(self, weights, deformers, indices):
        for weight, deformer_tuple, index_tpl, vertex in itertools.izip(weights, deformers, indices, self.vertices):
            vertex.weights = weight
            vertex.deformers = deformer_tuple
            vertex.deformer_indices = index_tpl

    def pack_weights(self):
        data = ['WGHT']
        data.append(struct.pack('<L', len(self.vertices) * 4 * 8 + 4))
        data.append(struct.pack('<L', len(self.vertices)))
        for vertex in self.vertices:
            data.append(vertex.pack_weights())
        return ''.join(data)

    def pack(self):
        data = [self.pack_positions(),
                self.pack_normals()]
        if self.uved:
            data.append(self.pack_uvs())
        if self.colored:
            data.append(self.pack_colors())
        if self.weighted:
            data.append(self.pack_weights())
        return ''.join(data)

    def add(self, vertex):
        '''Adds a vertex to the collection and sets
        its collection property.'''
        vertex.collection = self
        self.vertices.append(vertex)

    def __str__(self):
        return str(self.vertices)

    def __repr__(self):
        return str(self.vertices)

    def __getitem__(self, key):
        return self.vertices[key]

    def __len__(self):
        return len(self.vertices)


class ClothVertex(object):
    def __init__(self, pos, coll=None):
        if coll:
            self.collection = coll
        else:
            self.collection = None
        self.classname = 'ClothVertex'
        self.index = 0
        self.x = pos[0]
        self.y = pos[1]
        self.z = pos[2]
        self.u, self.v = 0.0, 0.0
        self.deformer = ''
        self.is_fixed = False

    def get_json(self):
        data = {
            'position': self.pos,
            'uv': self.uv,
            'deformer': self.deformer,
            'is_fixed': self.is_fixed,
        }
        return data

    @staticmethod
    def from_json(data, collection=None):
        v = ClothVertex()
        v.collection = collection
        v.pos = data['position']
        v.uv = data['uv']
        v.deformer = data['deformer']
        v.is_fixed = data['is_fixed']
        return v

    @property
    def pos(self):
        return self.x, self.y, self.z

    @pos.setter
    def pos(self, value):
        self.x, self.y, self.z = value

    @property
    def uv(self):
        return self.u, self.v

    @uv.setter
    def uv(self, value):
        self.u, self.v = value

    def pack_pos(self):
        '''Returns x, y, z packed into 3 floats.'''
        return struct.pack('<fff', *self.pos)

    def pack_uvs(self):
        '''Returns u, v packed into 2 floats.'''
        return struct.pack('<ff', *self.uv)


class ClothVertexCollection(Packer):
    def __init__(self, segm=None, verts=None):
        if segm:
            self.segment = segm
        else:
            self.segment = None
        if verts:
            self.vertices = verts
        else:
            self.vertices = []
        self.classname = 'ClothVertexCollection'
        self.uved = True

    def get_json(self):
        data = {
            'vertices': [v.get_json() for v in self.vertices],
            'uved': self.uved,
        }
        return data

    @staticmethod
    def from_json(data, segment=None):
        coll = ClothVertexCollection()
        coll.segment = segment
        coll.uved = data['uved']
        coll.vertices = [ClothVertex.from_json(vdata, coll) for vdata in data['vertices']]
        return coll

    def fixed(self):
        return [point for point in self.vertices if point.is_fixed]

    def fixed_indices(self):
        return [index for index, point in enumerate(self.vertices) if point.is_fixed]

    def get_deformers(self):
        return [point.deformer for point in self.vertices if point.deformer]

    def add(self, vert):
        '''Adds a vertex to the collection and sets its
        collection property.'''
        vert.collection = self
        self.vertices.append(vert)

    def pack_pos(self):
        '''Packs vertex positions into CPOS chunk.'''
        data = ['CPOS']
        data.append(struct.pack('<L', len(self.vertices) * 4 * 3 + 4))
        data.append(struct.pack('<L', len(self.vertices)))
        for vert in self.vertices:
            data.append(vert.pack_pos())
        return ''.join(data)

    def pack_uvs(self):
        data = ['CUV0']
        data.append(struct.pack('<L', len(self.vertices) * 4 * 2 + 4))
        data.append(struct.pack('<L', len(self.vertices)))
        for vert in self.vertices:
            data.append(vert.pack_uvs())
        return ''.join(data)

    def pack_fixed(self):
        data = ['FIDX', 'size', 'num']
        num = 0
        for index, vert in enumerate(self.vertices):
            if vert.is_fixed:
                data.append(struct.pack('<L', index))
                num += 1
        data[1] = struct.pack('<L', num * 4 + 4)
        data[2] = struct.pack('<L', num)
        return ''.join(data)

    def pack_weights(self):
        data = ['FWGT', 'size', 'num']
        num = 0
        data2 = []
        for index, vert in enumerate(self.vertices):
            if vert.is_fixed and vert.deformer:
                data2.append(self.null_terminate(vert.deformer))
                num += 1
        data.append(''.join(data2))
        data[1] = struct.pack('<L', len(data[3]) + 4)
        data[2] = struct.pack('<L', num)
        return ''.join(data)

    def __str__(self):
        return str(self.vertices)

    def __repr__(self):
        return str(self.vertices)

    def __getitem__(self, key):
        return self.vertices[key]

    def __len__(self):
        return len(self.vertices)


class Animation(Packer):
    # Params:
    #   - parent: Parent class(Msh)
    #   - empty: Empty animation?
    #       'empty' = empty animation
    #       'maybe_empty' = check .bones and .cycle before packing
    def __init__(self, msh=None, empty=None):
        # Ref to Msh.
        self.msh = msh
        self.bones = None
        self.cycle = None
        self.cycles = []
        self.classname = 'Animation'
        if empty == 'empty':
            # If the animation export is disabled, replace pack function.
            self.pack = self.pack_empty
        elif empty == 'maybe_empty':
            self.pack = self.pack_check

    @property
    def empty(self):
        '''Checks if this animation has any bones or cycle.'''
        if self.bones and self.cycle:
            return False
        return True

    def pack_check(self):
        if self.bones and self.cycle:
            return self.pack()
        else:
            return self.pack_empty()

    def pack(self):
        data = []
        data.append(self.bones.pack_SKL2())
        data.append(self.bones.pack_BLN2())
        data.append('ANM2')
        data.append('size')
        data.append(self.cycle.pack())
        data.append(self.bones.pack_KFR3())
        data[3] = struct.pack('<L', self.sum_seq(data, 4))
        return ''.join(data)

    def pack_empty(self):
        return ''


class Cycle(object):
    # animation: parent Animation
    # name: string
    # fps: float
    # style: int
    # frames: tuple2 (frame_start, frame_end)
    def __init__(self, animation=None):
        # Ref to Animation.
        self.animation = animation
        self.name = 'fullanimation'
        self.classname = 'AnimCycle'
        self.fps = 30
        self.style = 0
        self.frames = (1, 100)

    def numframes(self):
        return self.frames[1] - (self.frames[0] - 1)

    def animname(self):
        return self.name.ljust(64, '\x00')

    def pack(self):
        data = ['CYCL', struct.pack('<L', 84), struct.pack('<L', 1)]
        data.append(self.animname())
        data.append(struct.pack('<f', self.fps))
        data.append(struct.pack('<L', self.style))
        data.append(struct.pack('<LL', *self.frames))
        return ''.join(data)


class Bone(object):
    # Params:
    #   - collection: class(BoneCollection)
    def __init__(self, collection=None):
        # Parent BoneCollection.
        self.collection = collection
        self.classname = 'Bone'
        # Name of the bone(and it's accompanying Model).
        self.name = ''
        # CRC checksum of the bone.
        self.CRC = ''  # msh2_crc.crc(self.name)
        # The purpose of the following parameters is unclear.
        self.bone_type = 0
        self.constrain = 1.0
        self.bone1len = 0.0
        self.bone2len = 0.0
        self.blend_factor = 0
        self.keyframe_type = 0
        # List of position frames(x, y, z).
        self.pos_keyframes = None
        self.pos_keyframe_indices = None
        # List of rotation frames(x, y, z, w).
        self.rot_keyframes = None
        self.rot_keyframe_indices = None

    def dump(self, fh):
        w = fh.write
        w('BONE - {0}\n'.format(self.name))
        w('\tRotation:\n')
        for rot in self.rot_keyframes:
            w('\t\t{0}\n'.format(rot))
        w('\tTransform:\n')
        for pos in self.pos_keyframes:
            w('\t\t{0}\n'.format(pos))

    def recrc(self):
        '''Calculates a Zero CRC from the name.'''
        self.CRC = msh2_crc.strcrc(self.name)

    def set_name_from_crc(self):
        '''Tries to reverse-engineer the CRC into a name
        via comparing to the CRCs of all models in this .msh.'''
        if not self.CRC:
            raise MSH2Error('Bone doesnt have a CRC applied for reverse-engineering.')
        names = self.collection.get_check_names_list()
        name = msh2_crc.compare_crc_adv(names, self.CRC)
        if name:
            self.name = name
            self.collection.remove_check_name(name)

    def pack_SKL2(self):
        '''Packs attributes for the SKL2 chunk.'''
        data = [self.CRC,
                struct.pack('<L', self.bone_type),
                struct.pack('<f', self.constrain),
                struct.pack('<L', self.bone1len),
                struct.pack('<L', self.bone2len)]
        return ''.join(data)

    def pack_BLN2(self):
        '''Packs attributes for the BLN2 chunk.'''
        data = [self.CRC,
                struct.pack('<L', self.blend_factor)]
        return ''.join(data)

    def pack_KFR3(self):
        '''Packs position and rotation frames for the KFR3 chunk.'''
        data = [self.CRC,
                struct.pack('<L', self.keyframe_type),
                struct.pack('<L', len(self.pos_keyframes)),
                struct.pack('<L', len(self.rot_keyframes))]
        for ndx, frame in enumerate(self.pos_keyframes):
            data.append(struct.pack('<L', ndx + self.collection.animation.cycle.frames[0]))
            data.append(struct.pack('<fff', *frame))
        for ndx, frame in enumerate(self.rot_keyframes):
            data.append(struct.pack('<L', ndx + self.collection.animation.cycle.frames[0]))
            data.append(struct.pack('<ffff', *frame))
        return ''.join(data)


class BoneCollection(Packer):
    # Params:
    #   - animation: class(Animation)
    def __init__(self, animation=None):
        if animation:
            self.animation = animation
        else:
            self.animation = None
        self.classname = 'BoneCollection'
        self.bones = []
        self.check_names = None

    def add(self, bone):
        '''Adds bone to the collection and sets its
        collection attribute.'''
        bone.collection = self
        self.bones.append(bone)

    def remove(self, index):
        '''Remove bone at index index.'''
        del self.bones[index]

    def replace(self, bones):
        '''Replace internal bones list with bones.'''
        self.bones = bones

    def get_by_name(self, name):
        '''Get bone by name.'''
        for bone in self.bones:
            if name == bone.name:
                return bone

    def get_check_names_list(self):
        '''Returns list of all bone names.
        This list will be reduced if the name of a bone is found
        to maximize performance. It's used to calculate the name
        of a bone by comparing the CRC in the .msh file and a
        newly generated CRC of every bone in this list.'''
        if not self.check_names:
            self.check_names = self.animation.msh.models.get_names_list()
        return self.check_names

    def remove_check_name(self, name):
        '''If the name of a bone is matched with a CRC, remove
        the name from the list to reduce iteration time.'''
        self.check_names.remove(name)

    def __str__(self):
        return str(self.bones)

    def __repr__(self):
        return str(self.bones)

    def __getitem__(self, key):
        return self.bones[key]

    def __len__(self):
        return len(self.bones)

    def pack_SKL2(self):
        data = ['SKL2']
        data.append(struct.pack('<L', len(self.bones) * 20 + 4))
        data.append(struct.pack('<L', len(self.bones)))
        for bone in self.bones:
            data.append(bone.pack_SKL2())
        return ''.join(data)

    def pack_BLN2(self):
        data = ['BLN2']
        data.append(struct.pack('<L', len(self.bones) * 8 + 4))
        data.append(struct.pack('<L', len(self.bones)))
        for bone in self.bones:
            data.append(bone.pack_BLN2())
        return ''.join(data)

    def pack_KFR3(self):
        data = ['KFR3', 'size']
        data.append(struct.pack('<L', len(self.bones)))
        for bone in self.bones:
            data.append(bone.pack_KFR3())
        data[1] = struct.pack('<L', self.sum_seq(data, 3) + 4)
        return ''.join(data)


class Color(object):
    def __init__(self, color=None):
        if color:
            self.red = color[0]
            self.green = color[1]
            self.blue = color[2]
            self.alpha = color[3]
        else:
            self.red = 128
            self.green = 128
            self.blue = 128
            self.alpha = 255
        self.classname = 'Color'

    def get_json(self):
        data = {
            'rgba': self.rgba,
        }
        return data

    @staticmethod
    def from_json(data):
        col = Color()
        col.rgba = data['rgba']
        return col

    @property
    def rgba(self):
        return self.red, self.green, self.blue, self.alpha

    @rgba.setter
    def rgba(self, value):
        self.red, self.green, self.blue, self.alpha = value

    def get_f(self):
        if isinstance(self.red, float):
            return self.red, self.green, self.blue, self.alpha
        else:
            return ((self.red / 255.), (self.green / 255.),
                    (self.blue / 255.), (self.alpha / 255.))

    def get_b(self):
        if isinstance(self.red, float):
            return (int(self.red * 255), int(self.green * 255),
                    int(self.blue * 255), int(self.alpha * 255))
        else:
            return self.red, self.green, self.blue, self.alpha

    def get(self):
        return self.red, self.green, self.blue, self.alpha

    def set(self, r, g, b, a=255):
        self.red = r
        self.green = g
        self.blue = b
        self.alpha = a

    def __str__(self):
        return '{0}, {1}, {2}, {3}'.format(self.red, self.green, self.blue, self.alpha)

    def __repr__(self):
        return self.__str__()

    def pack(self, mode='B'):
        '''Packs color channels, default type is B(bool).
        No converting is done, so if you pass f for mode
        but the values are from 0-255 you will get that
        value as float.'''
        return struct.pack('<{0}'.format(mode * 4),
                           self.red,
                           self.green,
                           self.blue,
                           self.alpha)


class Transform(object):
    def __init__(self, tra=None, rot=None, sca=None):
        if rot:
            self.rotation = rot
        else:
            self.rotation = 0.0, 0.0, 0.0, 1.0
        if tra:
            self.translation = tra
        else:
            self.translation = 0.0, 0.0, 0.0
        if sca:
            self.scale = sca
        else:
            self.scale = 1.0, 1.0, 1.0
        self.classname = 'Transform'

    def get_json(self):
        data = {
            'position': self.translation,
            'rotation': self.euler_angles(),
            'scale': self.scale,
        }
        return data

    @classmethod
    def from_json(cls, data):
        tr = cls()
        tr.translation = data['position']
        tr.rotation = tr.euler_to_quaternion(data['rotation'])
        tr.scale = data['scale']
        return tr

    def __str__(self):
        return 'Pos({0}), Rot({1}), Scl({2})'.format(', '.join([str(i) for i in self.translation]),
                                                     ', '.join([str(i) for i in self.rotation]),
                                                     ', '.join([str(i) for i in self.scale]))

    def __repr__(self):
        return 'Pos({0}), Rot({1}), Scl({2})'.format(', '.join([str(i) for i in self.translation]),
                                                     ', '.join([str(i) for i in self.rotation]),
                                                     ', '.join([str(i) for i in self.scale]))

    def pack(self):
        data = ['TRAN', struct.pack('<L', 40)]
        data.append(struct.pack('<fff', *self.scale))
        data.append(struct.pack('<ffff', *self.rotation))
        data.append(struct.pack('<fff', *self.translation))
        return ''.join(data)

    def euler_angles(self):
        '''Returns the internal Quaternion in Euler Angles(radians).'''
        test = self.rotation[0] * self.rotation[1] + self.rotation[2] * self.rotation[3]
        if test > 0.499:
            heading = 2 * math.atan2(self.rotation[0], self.rotation[3])
            attitude = math.pi / 2
            bank = 0
            return math.degrees(heading), math.degrees(attitude), math.degrees(bank)
        elif test < -0.499:
            heading = -2 * math.atan2(self.rotation[0], self.rotation[3])
            attitude = -1 * math.pi / 2
            bank = 0
            return math.degrees(heading), math.degrees(attitude), math.degrees(bank)
        sqx = self.rotation[0] * self.rotation[0]
        sqy = self.rotation[1] * self.rotation[1]
        sqz = self.rotation[2] * self.rotation[2]
        heading = math.atan2((2 * self.rotation[1] * self.rotation[3] -
                             2 * self.rotation[0] * self.rotation[2]),
                             1 - 2 * sqy - 2 * sqz)
        attitude = math.asin(2 * test)
        bank = math.atan2((2 * self.rotation[0] * self.rotation[3] -
                          2 * self.rotation[1] * self.rotation[2]),
                          1 - 2 * sqx - 2 * sqz)
        return math.degrees(heading), math.degrees(attitude), math.degrees(bank)

    def euler_to_quaternion(self, euler):
        c1 = math.cos(math.radians(euler[0] / 2))
        s1 = math.sin(math.radians(euler[0] / 2))
        c2 = math.cos(math.radians(euler[1] / 2))
        s2 = math.sin(math.radians(euler[1] / 2))
        c3 = math.cos(math.radians(euler[2] / 2))
        s3 = math.sin(math.radians(euler[2] / 2))
        c1c2 = c1 * c2
        s1s2 = s1 * s2
        w = c1c2 * c3 - s1s2 * s3
        x = c1c2 * s3 + s1s2 * c3
        y = s1 * c2 * c3 + c1 * s2 * s3
        z = c1 * s2 * c3 - s1 * c2 * s3
        self.rotation = x, y, z, w
        return x, y, z, w

    def reversed_quaternion(self):
        '''Returns the Quaternion as W, X, Y, Z.'''
        return self.rotation[3], self.rotation[0], self.rotation[1], self.rotation[2]


class BBox(Transform):
    def __init__(self):
        self.rotation = 0.0, 0.0, 0.0, 1.0
        self.extents = 4.0, 4.0, 4.0
        self.center = 0.0, 0.0, 0.0
        self.radius = 6.92
        self.classname = 'BBox'

    def get_json(self):
        data = {
            'rotation': self.euler_angles(),
            'extents': self.extents,
            'center': self.center,
            'radius': self.radius,
        }
        return data

    @staticmethod
    def from_json(data):
        b = BBox()
        b.rotation = b.euler_to_quaternion(data['rotation'])
        b.extents = data['extents']
        b.center = data['center']
        b.radius = data['radius']
        return b

    def pack(self):
        data = ['BBOX', struct.pack('<L', 44)]
        data.append(struct.pack('<ffff', *self.rotation))
        data.append(struct.pack('<fff', *self.center))
        data.append(struct.pack('<fff', *self.extents))
        data.append(struct.pack('<f', self.radius))
        return ''.join(data)
