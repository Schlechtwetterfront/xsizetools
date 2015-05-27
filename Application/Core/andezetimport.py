#########################################################
#####               andezetimport                   #####
#####                                               #####
#####            Main Import classes                #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################
import os
import sys
import logging
reload(logging)
import softimage
reload(softimage)
import andezetcore
reload(andezetcore)
from pythoncom import com_error
import msh2
reload(msh2)
import msh2_unpack
reload(msh2_unpack)
from msh2_crc import CRCError
from datetime import datetime as dt
import win32com
from win32com.client import constants as const

xsimath = win32com.client.Dispatch('XSI.Math')
xsifact = win32com.client.Dispatch('XSI.Factory')

STR_CODEC = 'utf-8'


class MshImportError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class MaterialBuilder(object):
    def __init__(self, imp, msh):
        self.msh = msh
        self.imp = imp
        self.xsi = self.imp.xsi
        self.pb = self.imp.pb

    def build(self):
        logging.info('Building {0} materials.'.format(len(self.msh.materials)))
        coll = self.msh.materials
        if len(coll) < 1:
            logging.debug('No materials in collection.')
            return ()
        matlib = self.xsi.ActiveProject.ActiveScene.ActiveMaterialLibrary
        materials = {}
        for mat in coll:
            logging.info('Building Material {0}.'.format(mat.name))
            simat = matlib.CreateMaterial('Phong', mat.name)
            # Colors.
            shader = simat.Shaders(0)
            col = shader.Parameters('diffuse').Value
            col.Red = mat.diff_color.red
            col.Green = mat.diff_color.green
            col.Blue = mat.diff_color.blue
            col.Alpha = mat.diff_color.alpha

            col = shader.Parameters('ambient').Value
            col.Red = mat.ambt_color.red
            col.Green = mat.ambt_color.green
            col.Blue = mat.ambt_color.blue
            col.Alpha = mat.ambt_color.alpha

            col = shader.Parameters('specular').Value
            col.Red = mat.spec_color.red
            col.Green = mat.spec_color.green
            col.Blue = mat.spec_color.blue
            col.Alpha = mat.spec_color.alpha

            shader.Parameters('shiny').Value = mat.gloss

            # Image.
            if mat.tex0:
                if self.imp.config.get('btexpath'):
                    imgfolder = self.imp.config.get('texpath')
                else:
                    imgfolder = os.path.dirname(self.imp.config.get('path'))
                imgshader = self.xsi.CreateShaderFromPreset('$XSI_DSPRESETS\\Shaders\\Texture\\Image.Preset', simat)
                imgpath = os.path.join(imgfolder, mat.tex0)
                img_clip = self.xsi.SICreateImageClip2(imgpath)
                self.xsi.SIConnectShaderToCnxPoint(img_clip, imgshader.tex, False)
                self.xsi.SIConnectShaderToCnxPoint(imgshader, simat.Shaders(0).Parameters('diffuse'), False)
            # ZEFlags.
            simat2 = self.get_si_mat(mat)
            if simat2:
                self.add_flag_prop(simat2, mat)
            materials[mat.name] = simat
            logging.info('Finished building {0}.'.format(mat.name))
        logging.info('Finished building materials.')
        return materials

    def get_si_mat(self, mat):
        name = mat.name
        mats = self.imp.material_name_dict()
        try:
            mat = mats[name]
            return mat
        except KeyError:
            logging.exception('Couldnt find material {0}.'.format(name))
            return None

    def add_flag_prop(self, simat, mat):
        pset = simat.AddProperty('CustomProperty', False, 'ZeroEngine Flags')
        pset.AddParameter3('tex1', const.siString, mat.tex1)
        pset.AddParameter3('tex2', const.siString, mat.tex2)
        pset.AddParameter3('tex3', const.siString, mat.tex3)

        if mat.flags[4][1]:
            transp = 2
        elif mat.flags[5][1]:
            transp = 1
        else:
            transp = 0
        pset.AddParameter3('emissive', const.siBool, mat.flags[7][1], '', '', 0)
        pset.AddParameter3('glow', const.siBool, mat.flags[6][1], '', '', 0)
        pset.AddParameter3('transparency', const.siInt4, transp, 0, 2, 0)
        pset.AddParameter3('hardedged', const.siBool, mat.flags[3][1], '', '', 0)
        pset.AddParameter3('perpixel', const.siBool, mat.flags[2][1], '', '', 0)
        pset.AddParameter3('additive', const.siBool, mat.flags[1][1], '', '', 0)
        pset.AddParameter3('specular', const.siBool, mat.flags[0][1], '', '', 0)
        pset.AddParameter3('rendertype', const.siInt4, mat.render_type, 0, 31, 0)
        pset.AddParameter3('data0', const.siInt4, mat.data0, 0, 255, 0)
        pset.AddParameter3('data1', const.siInt4, mat.data1, 0, 255, 0)

        lay = pset.PPGLayout

        lay.AddGroup('ZeroEngine Material Flags', 1)
        lay.AddGroup('Additional Textures', 1)
        lay.AddItem('tex1', 'Texture 1')
        lay.AddItem('tex2', 'Texture 2')
        lay.AddItem('tex3', 'Texture 3')
        lay.EndGroup()
        lay.AddGroup('Flags', 1)
        lay.AddItem('emissive', 'Emissive')
        lay.AddItem('glow', 'Glow')
        lay.AddItem('transparency', 'Transparency')
        lay.AddItem('hardedged', 'Hardedged Transparency')
        lay.AddItem('perpixel', 'Per-Pixel Lighting')
        lay.AddItem('additive', 'Additive Transparency')
        lay.AddItem('specular', 'Specular')
        lay.AddItem('rendertype', 'RenderType')
        lay.AddItem('data0', 'Data0')
        lay.AddItem('data1', 'Data1')
        lay.EndGroup()
        lay.EndGroup()


class ChainItemBuilder(softimage.SIModel):
    prim_types = {0: 'Sphere',
                  1: 'Sphere',
                  2: 'Cylinder',
                  4: 'Cube'}
    cloth_prim_types = {0: 'Sphere',
                        1: 'Cylinder'}

    def __init__(self, model, chainbuilder):
        self.model = model
        self.chainbuilder = chainbuilder
        self.xsi = self.chainbuilder.xsi
        self.imp = self.chainbuilder.imp
        if self.imp.config.get('ignoregeo'):
            self.build_geo = self.build_null
            self.build_prim = self.build_null
            self.build_shadow = self.build_null

    def build(self):
        if self.model.model_type == 'null' or self.model.model_type == 'bone':
            self.build_null()
        elif self.model.model_type == 'geoshadow':
            self.build_shadow()
        elif 'geo' in self.model.model_type:
            if self.model.collprim:
                self.build_prim()
            elif self.model.name.startswith('c_'):
                self.build_c_prim()
            else:
                self.build_geo()
        elif self.model.model_type == 'cloth':
            self.build_cloth()
        else:
            raise MshImportError('Unsupported model type {0} on {1}.'.format(self.model.model_type,
                                                                             self.model.name))
        logging.info('Finished building {0}.'.format(self.model.name))
        return self.si_model

    def build_cloth(self):
        logging.info('Building {0} as cloth(originally {1}).'.format(self.model.name, self.model.model_type))
        vertex_positions = self.get_vertex_positions()
        faces = self.get_faces()
        if self.model.parent_name:
            parent = self.chainbuilder.name_dict[self.model.parent_name]
        else:
            parent = self.xsi.ActiveSceneRoot
        if not parent:
            logging.error('Cant find parent {0} for {1}.'.format(self.model.parent_name,
                                                                 self.model.name))
        try:
            self.si_model = parent.AddPolygonMesh(vertex_positions,
                                                  faces,
                                                  self.model.name)
        except com_error:
            logging.exception('verts: {0}, faces: {1}, name: {2}.'.format(vertex_positions,
                                                                          faces, self.model.name))
            self.imp.abort_checklog()
        self.geo = self.si_model.ActivePrimitive.GetGeometry2(0)
        if self.model.vis == 1:
            self.xsi.ToggleVisibility(self.si_model, None, None)
        if self.model.segments[0].vertices.uved:
            uvs = self.make_uvs_persample()
            self.xsi.CreateProjection(self.si_model)
            self.xsi.FreezeObj(self.si_model)
            self.set_uvs(0, uvs)
        else:
            logging.debug('Model {0} has no UVs.'.format(self.model.name))
        self.set_transform()
        self.set_vis()

    def build_shadow(self):
        logging.info('Building {0} as shadow(originally {1}).'.format(self.model.name, self.model.model_type))
        self.si_model = self.xsi.GetPrim('Null', '{0}(shadow)'.format(self.model.name), self.model.parent_name)
        self.set_transform()
        self.set_vis()

    def build_c_prim(self):
        logging.info('Building {0} as cloth prim(originally {1}).'.format(self.model.name, self.model.model_type))

        # Find a cloth which has this cloth primitive as cloth collision so we can retrieve the necessary primitive data.
        my_collision = None
        for model in self.imp.msh.models:
            if model.model_type == 'cloth':
                cloth_geo = model.segments[0]
                for collision in cloth_geo.collisions:
                    print self.model.name, len(self.model.name)
                    print collision.name, len(collision.name)
                    if collision.name == self.model.name:
                        my_collision = collision
                        print 'Found it'
                        break

        self.si_model = self.xsi.CreatePrim(self.cloth_prim_types[my_collision.primitive_type],
                                            'MeshSurface',
                                            self.model.name,
                                            self.model.parent_name)
        self.set_transform()
        self.set_vis()
        # self.add_prim_property()
        if my_collision.primitive_type == 0:
            self.si_model.radius = my_collision.collision_prim[0]
            self.set_cloth_prim_scale(my_collision)
        elif my_collision.primitive_type == 1:
            self.si_model.radius = my_collision.collision_prim[0]
            self.si_model.height = my_collision.collision_prim[1]
            self.set_cloth_prim_scale(my_collision)
        else:
            logging.error('{0} is unknown prim type({1}).'.format(self.model.name, self.model.primitive[0]))

    def build_prim(self):
        logging.info('Building {0} as prim(originally {1}).'.format(self.model.name, self.model.model_type))
        if self.model.primitive[0] == 3:
            logging.error('Primitive {0} is of type 3. Invalid. Building null instead.'.format(self.model.name))
            self.imp.notify('Primitive {0} is of type 3. Invalid. Building null instead.'.format(self.model.name))
            self.build_null()
            return
        self.si_model = self.xsi.CreatePrim(self.prim_types[self.model.primitive[0]],
                                            'MeshSurface',
                                            self.model.name,
                                            self.model.parent_name)
        self.set_transform()
        self.set_vis()
        self.add_prim_property()
        if self.model.primitive[0] == 0:
            self.si_model.radius = self.model.primitive[1]
            self.set_prim_scale()
        elif self.model.primitive[0] == 1:
            self.si_model.radius = self.model.primitive[1]
            self.set_prim_scale()
        elif self.model.primitive[0] == 2:
            self.si_model.radius = self.model.primitive[1]
            self.si_model.height = self.model.primitive[2]
            self.set_prim_scale()
        elif self.model.primitive[0] == 4:
            self.si_model.length = 1.0
            self.set_prim_scale()
        else:
            logging.error('{0} is unknown prim type({1}).'.format(self.model.name, self.model.primitive[0]))

    def add_prim_property(self):
        property_set = self.si_model.AddProperty('CustomProperty', False, 'collprim')
        property_set.AddParameter3('type', const.siInt4, self.model.primitive[0])

    def set_prim_scale(self):
        if self.model.parent_name:
            parent = self.chainbuilder.name_dict[self.model.parent_name]
        else:
            parent = self.xsi.ActiveSceneRoot
        parent_transform = parent.Kinematics.Local.Transform
        transform = self.si_model.Kinematics.Local.Transform
        if self.model.primitive[0] == 4:
            transform.SetScalingFromValues(self.model.primitive[1] / parent_transform.SclX,
                                           self.model.primitive[2] / parent_transform.SclY,
                                           self.model.primitive[3] / parent_transform.SclZ)
        else:
            transform.SetScalingFromValues(1.0 / parent_transform.SclX,
                                           1.0 / parent_transform.SclY,
                                           1.0 / parent_transform.SclZ)
        self.si_model.Kinematics.Local.Transform = transform

    def set_cloth_prim_scale(self, collision):
        if self.model.parent_name:
            parent = self.chainbuilder.name_dict[self.model.parent_name]
        else:
            parent = self.xsi.ActiveSceneRoot
        parent_transform = parent.Kinematics.Local.Transform
        transform = self.si_model.Kinematics.Local.Transform
        transform.SetScalingFromValues(1.0 / parent_transform.SclX,
                                       1.0 / parent_transform.SclY,
                                       1.0 / parent_transform.SclZ)
        self.si_model.Kinematics.Local.Transform = transform

    def build_geo(self):
        logging.info('Building {0} as polymesh(originally {1}).'.format(self.model.name, self.model.model_type))
        vertex_positions = self.get_vertex_positions()
        faces = self.get_faces()
        if self.model.parent_name:
            parent = self.chainbuilder.name_dict[self.model.parent_name]
        else:
            parent = self.xsi.ActiveSceneRoot
        if not parent:
            logging.error('Cant find parent {0} for {1}.'.format(self.model.parent_name,
                                                                 self.model.name))
        if len(vertex_positions) == 0:
            logging.info('Building {0} as null (originally {1}) because no geometry information was found.'.format(self.model.name, self.model.model_type))
            self.build_null()
            return
        try:
            self.si_model = parent.AddPolygonMesh(vertex_positions,
                                                  faces,
                                                  self.model.name)
        except com_error:
            logging.exception('verts: {0}, faces: {1}, name: {2}.'.format(vertex_positions,
                                                                          faces, self.model.name))
            self.imp.abort_checklog()
        self.geo = self.si_model.ActivePrimitive.GetGeometry2(0)
        # Normals
        normal_cluster = self.geo.AddCluster(const.siSampledPointCluster)
        normal_cluster.AddProperty('User Normal Property', False, 'ZETools-NormalsProperty')
        self.set_normals(0, self.make_normals())
        if self.model.vis == 1:
            self.xsi.ToggleVisibility(self.si_model, None, None)
        if self.model.segments[0].vertices.uved:
            uvs = self.make_uvs_persample()
            self.xsi.CreateProjection(self.si_model)
            self.xsi.FreezeObj(self.si_model)
            self.set_uvs(0, uvs)
        else:
            logging.debug('Model {0} has no UVs.'.format(self.model.name))
        if len(self.model.segments) > 1:
            logging.debug('Model {0} has {1} segments, creating poly clusters.'.format(self.model.name, len(self.model.segments)))
            self.create_poly_clusters()
        else:
            self.xsi.SIAssignMaterial(self.si_model,
                                      self.chainbuilder.materials[self.model.segments[0].material.name])
        if self.model.segments[0].vertices.colored:
            colors = self.make_colors_persample()
            self.xsi.CreateVertexColorSupport('', 'Vertex_Color', [self.si_model])
            self.set_vertex_colors(0, colors)
        else:
            logging.debug('Model {0} is not colored.'.format(self.model.name))
        self.set_transform()
        self.set_vis()

    def make_normals(self):
        '''Creates Normals.'''
        numsamples = self.geo.Samples.Count
        normals = [[0.0] * numsamples, [0.0] * numsamples, [0.0] * numsamples]
        # Will offset the index by the number of vertices the precedent
        # segments had.
        offset = 0
        for segm in self.model.segments:
            numverts = len(segm.vertices)
            for n in xrange(numverts):
                vert = segm.vertices[n]
                point = self.geo.Points[n + offset]
                for sample in point.Samples:
                    normals[0][sample.Index] = vert.nx
                    normals[1][sample.Index] = vert.ny
                    normals[2][sample.Index] = vert.nz
            offset += numverts
        logging.debug('Created UVs for {0} samples/nodes.'.format(numsamples))
        return normals

    def make_colors_persample(self):
        numsamples = self.geo.Samples.Count
        colors = [[0.0] * numsamples,
                 [0.0] * numsamples,
                 [0.0] * numsamples,
                 [0.0] * numsamples]
        # Will offset the index by the number of vertices the precedent
        # segments had.
        offset = 0
        for segm in self.model.segments:
            numverts = len(segm.vertices)
            for n in xrange(numverts):
                vert = segm.vertices[n]
                point = self.geo.Points[n + offset]
                for sample in point.Samples:
                    col = vert.color.get_f()
                    colors[0][sample.Index] = col[0]
                    colors[1][sample.Index] = col[1]
                    colors[2][sample.Index] = col[2]
                    colors[3][sample.Index] = col[3]
            offset += numverts
        logging.debug('Created Vertex Colors for {0} samples/nodes.'.format(numsamples))
        return colors

    def create_poly_clusters(self):
        offset = 0
        cls_debug = []
        for seg in self.model.segments:
            cls = self.geo.AddCluster('poly', 'zeimport_poly', range(offset, len(seg.faces) + offset))
            self.xsi.SIAssignMaterial(cls, self.chainbuilder.materials[seg.material.name])
            cls_debug.append(cls.Name)
            offset += len(seg.faces)
        logging.debug('Created {0} poly clusters({1}).'.format(len(cls_debug), ', '.join(cls_debug)))

    def get_vertex_positions(self):
        v_pos = []
        for segment in self.model.segments:
            for vert in segment.vertices:
                v_pos.extend(vert.pos)
        logging.debug('Retrieved {0} vertex positions.'.format(len(v_pos) / 3))
        return v_pos

    def get_faces(self):
        faces = []
        offset = 0
        numfaces = 0
        for segment in self.model.segments:
            for face in segment.faces:
                numfaces += 1
                faces.append(face.sides)
                sii = face.SIindices()
                if len(sii) == 4:
                    sii = (sii[0] + offset, sii[1] + offset,
                           sii[2] + offset, sii[3] + offset)
                else:
                    sii = sii[0] + offset, sii[1] + offset, sii[2] + offset
                faces.extend(sii)
            offset += len(segment.vertices)
        logging.debug('Created {0} faces.'.format(numfaces))
        return faces

    def make_uvs_persample(self):
        '''Creates UVs if the mesh has more samples than points.'''
        numsamples = self.geo.Samples.Count
        uvs = [[0.0] * numsamples, [0.0] * numsamples, [0.0] * numsamples]
        # Will offset the index by the number of vertices the precedent
        # segments had.
        offset = 0
        for segm in self.model.segments:
            numverts = len(segm.vertices)
            for n in xrange(numverts):
                vert = segm.vertices[n]
                point = self.geo.Points[n + offset]
                for sample in point.Samples:
                    uvs[0][sample.Index] = vert.u
                    uvs[1][sample.Index] = vert.v
            offset += numverts
        logging.debug('Created UVs for {0} samples/nodes.'.format(numsamples))
        return uvs

    def make_uvs(self):
        '''Creates UVs if the number of points equals the number of
        samples.'''
        uvs = [[], []]
        for seg in self.model.segments:
            for v in seg.vertices:
                uvs[0].append(v.u)
                uvs[1].append(v.v)
        uvs.append([0.0] * self.model.segments.num_vertices())

        return uvs

    def build_null(self):
        logging.info('Building {0} as null(originally {1}).'.format(self.model.name, self.model.model_type))
        self.si_model = self.xsi.GetPrim('Null', self.model.name, self.model.parent_name)
        # Set Null display size.
        self.si_model.Parameters('Size').Value = float(self.imp.config.get('nullsize'))
        if self.imp.config.get('wirecol'):
            if 'eff' in self.model.name:
                col = self.imp.config.get('effcol')
                r, g, b = [float(item) for item in col.split(' ')]
                wirecol = self.chainbuilder.scn.wirecol(r, g, b)
                display = self.si_model.Properties('Display')
                if display.IsA(const.siSharedPSet):
                    display = self.xsi.MakeLocal(display, const.siNodePropagation)[0]
                display.wirecol.Value = wirecol
            elif 'root' in self.model.name:
                col = self.imp.config.get('rootcol')
                r, g, b = [float(item) for item in col.split(' ')]
                wirecol = self.chainbuilder.scn.wirecol(r, g, b)
                display = self.si_model.Properties('Display')
                if display.IsA(const.siSharedPSet):
                    display = self.xsi.MakeLocal(display, const.siNodePropagation)[0]
                display.wirecol.Value = wirecol
            elif 'bone' in self.model.name:
                col = self.imp.config.get('bonecol')
                r, g, b = [float(item) for item in col.split(' ')]
                wirecol = self.chainbuilder.scn.wirecol(r, g, b)
                display = self.si_model.Properties('Display')
                if display.IsA(const.siSharedPSet):
                    display = self.xsi.MakeLocal(display, const.siNodePropagation)[0]
                display.wirecol.Value = wirecol
        if self.imp.config.get('hideeffs'):
            if 'eff' in self.model.name:
                if self.model.vis != 1:
                    self.xsi.ToggleVisibility(self.si_model, None, None)
        elif self.imp.config.get('hideroots'):
            if 'root' in self.model.name:
                if self.model.vis != 1:
                    self.xsi.ToggleVisibility(self.si_model, None, None)
        else:
            self.set_vis()
        self.set_transform()

    def set_vis(self):
        if self.model.vis == 1:
            self.xsi.ToggleVisibility(self.si_model, None, None)

    def set_transform(self):
        if ('geo' in self.model.model_type) and self.model.collprim and 'p_' in self.si_model.Parent.FullName:
            transform = self.si_model.Kinematics.Local.Transform
            # parent_transform = self.si_model.Kinematics.Local.Transform
            quat = xsimath.CreateQuaternion()
            quat.Set(*self.model.transform.reversed_quaternion())
            transform.SetRotationFromQuaternion(quat)
            # It seems we have to pipe the transform in we got before.
            self.si_model.Kinematics.Local.Transform = transform
            transform = self.si_model.Kinematics.Global.Transform
            transform.SetScalingFromValues(*self.model.transform.scale)
            pos = self.model.transform.translation
            transform.SetTranslationFromValues(pos[0],
                                               pos[1],
                                               pos[2])
            self.si_model.Kinematics.Global.Transform = transform
            logging.debug('''Set global tranform for {0} to:
\t\t\t\t\t\t\tPosition: {1}, {2}, {3};
\t\t\t\t\t\t\tRotation: {4}, {5}, {6};
\t\t\t\t\t\t\tScale:    {7}, {8}, {9}.'''.format(self.si_model.Name,
                                               transform.PosX, transform.PosY, transform.PosZ,
                                               transform.RotX, transform.RotY, transform.RotZ,
                                               transform.SclX, transform.SclY, transform.SclZ))

        else:
            transform = self.si_model.Kinematics.Local.Transform
            transform.SetTranslationFromValues(*self.model.transform.translation)
            quat = xsimath.CreateQuaternion()
            quat.Set(*self.model.transform.reversed_quaternion())
            transform.SetRotationFromQuaternion(quat)
            transform.SetScalingFromValues(*self.model.transform.scale)
            # It seems we have to pipe the transform in we got before.
            self.si_model.Kinematics.Local.Transform = transform
            logging.debug('''Set local tranform for {0} to:
\t\t\t\t\t\t\tPosition: {1}, {2}, {3};
\t\t\t\t\t\t\tRotation: {4}, {5}, {6};
\t\t\t\t\t\t\tScale:    {7}, {8}, {9}.'''.format(self.si_model.Name,
                                               transform.PosX, transform.PosY, transform.PosZ,
                                               transform.RotX, transform.RotY, transform.RotZ,
                                               transform.SclX, transform.SclY, transform.SclZ))


class ChainBuilder(object):
    def __init__(self, imp, msh, materials=None):
        self.msh = msh
        # imp = Import. Can't use import, can I?
        self.imp = imp
        self.xsi = self.imp.xsi
        self.pb = self.imp.pb
        self.materials = materials
        self.scn = softimage.SIScene()
        self.name_dict = {}

    def build(self):
        logging.info('Starting chain builder({0} Models).'.format(len(self.msh.models)))
        coll = self.msh.models
        lencoll = len(coll)
        self.pb.set(lencoll, 'Building chain...')
        chain = []
        for ind, model in enumerate(coll):
            self.pb.setc('Building {0}({1}/{2})...'.format(model.name,
                                                           ind, lencoll))
            builder = ChainItemBuilder(model, self)
            item = builder.build()
            self.name_dict[model.name] = item
            chain.append(item)
            self.pb.inc()
        logging.info('Finished chain builder.')
        return chain


class AnimationImport(object):
    def __init__(self, imp, chain, bones):
        # imp = Import. Can't use import, can I?
        self.imp = imp
        self.chain = chain
        self.bonecoll = bones
        self.pb = self.imp.pb

    def import_(self):
        logging.info('Starting animation import.')
        if not self.bonecoll:
            logging.debug('No BoneCollection in Animation.')
            return
        if not self.chain:
            logging.debug('No chain.')
            return
        lencoll = len(self.chain)
        self.pb.set(lencoll, 'Applying animation...')
        for ind, link in enumerate(self.chain):
            self.pb.setc('Animating {0}({1}/{2})...'.format(link.Name,
                                                            ind, lencoll))
            logging.info('Animating {0}.'.format(link.Name))
            bone = self.bonecoll.get_by_name(link.Name)
            if not bone:
                logging.debug('No msh2 Bone for {0}, continuing.'.format(link.Name))
                continue
            start_frame = self.bonecoll.animation.cycle.frames[0]
            # Position:
            keys_x = []
            keys_y = []
            keys_z = []
            for frame, position in enumerate(bone.pos_keyframes):
                keys_x.append(frame + start_frame)
                keys_x.append(position[0])
                keys_y.append(frame + start_frame)
                keys_y.append(position[1])
                keys_z.append(frame + start_frame)
                keys_z.append(position[2])
            # Animate every angle independently.
            link.posx.AddFCurve(None, const.siLinearInterpolation, None, keys_x)
            link.posy.AddFCurve(None, const.siLinearInterpolation, None, keys_y)
            link.posz.AddFCurve(None, const.siLinearInterpolation, None, keys_z)
            # Rotation:
            keys_x = []
            keys_y = []
            keys_z = []
            for frame, rotation in enumerate(bone.rot_keyframes):
                quat = xsimath.CreateQuaternion()
                quat.Set(rotation[3], rotation[0], rotation[1], rotation[2])
                # Get radians rotation values from quaternion.
                x, y, z = quat.GetXYZAngleValues2()
                keys_x.append(frame + start_frame)
                keys_x.append(xsimath.RadiansToDegrees(x))
                keys_y.append(frame + start_frame)
                keys_y.append(xsimath.RadiansToDegrees(y))
                keys_z.append(frame + start_frame)
                keys_z.append(xsimath.RadiansToDegrees(z))
            # Animate every angle independently.
            link.rotx.AddFCurve(None, const.siLinearInterpolation, None, keys_x)
            link.roty.AddFCurve(None, const.siLinearInterpolation, None, keys_y)
            link.rotz.AddFCurve(None, const.siLinearInterpolation, None, keys_z)
            self.pb.inc()
            logging.info('Finished animating {0}.'.format(link.Name))
        logging.info('Finished animation import.')


class Enveloper(object):
    def __init__(self, imp, msh, chain):
        self.imp = imp
        self.msh = msh
        self.chain = chain
        self.xsi = self.imp.xsi

    def envelope(self):
        logging.info('Starting enveloping.')
        for item in self.chain:
            logging.info('Enveloping {0}.'.format(item.Name))
            model = self.msh.models.by_name(item.Name)
            if not model:
                logging.debug('No msh2 Model found for {0}, continuing.'.format(item.Name))
                continue
            if (model.model_type == 'cloth') and (model.deformers):
                logging.debug('Model is cloth, trying some stuff.')
                deformers = self.imp.get_objects_by_name(model.deformers)
                coll = xsifact.CreateObject('XSI.Collection')
                coll.AddItems(deformers)
                item.ApplyEnvelope(coll)
                weights = self.make_cloth_weights(model)
                simd = softimage.SIModel(item)
                simd.set_weights(0, weights)
                logging.info('Finished enveloping {0}.'.format(item.Name))
                continue
            if not model.deformers:
                logging.debug('No deformers for msh2 Model {0}, continuing.'.format(model.name))
                continue
            deformers = self.imp.get_objects_by_name(model.deformers)
            coll = xsifact.CreateObject('XSI.Collection')
            coll.AddItems(deformers)
            item.ApplyEnvelope(coll)
            weights = self.make_weights(model)
            simd = softimage.SIModel(item)
            simd.set_weights(0, weights)
            logging.info('Finished enveloping {0}.'.format(item.Name))
        logging.info('Finished enveloping.')

    def make_cloth_weights(self, model):
        weights = []
        num_deformers = len(model.deformers)
        segment = model.segments[0]
        for n in xrange(num_deformers):
            weights.append([0.0] * len(segment.vertices))
        for vind, vert in enumerate(segment.vertices):
            if vert.deformer:
                deformer_index = model.deformers.index(vert.deformer)
                logging.debug('Vert: {0} - {1} - {2}'.format(vind, vert.deformer, deformer_index))
                weights[deformer_index][vind] = 100
            else:
                weights[0][vind] = 100
        logging.debug('Created weights for {0} cloth points.'.format(len(weights[0])))
        return weights

    def make_weights(self, model):
        weights = []
        num_deformers = len(model.deformers)
        offset = 0
        for n in xrange(num_deformers):
            weights.append([0.0] * model.segments.num_vertices())
        for seg in model.segments:
            for vind, vert in enumerate(seg.vertices):
                for weight, deformer_ind in zip(vert.weights, vert.deformer_indices):
                    if weight > 0.0:
                        weights[deformer_ind][vind + offset] = weight * 100
            offset += len(seg.vertices)
        logging.debug('Created weights for {0} points.'.format(len(weights[0])))
        return weights


class Import(softimage.SIGeneral):
    def __init__(self, app, config=None):
        self.msh = None
        self.xsi = app
        self.config = config
        self.notifications = None
        self.stats = None
        self.pb = softimage.SIProgressBar()
        logpath = os.path.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'import_log.log')
        logging.basicConfig(format='%(levelname)s (%(lineno)d, %(funcName)s): %(message)s',
                            filename=logpath,
                            filemode='w',
                            level=logging.DEBUG)

    def notify(self, text):
        if self.notifications:
            self.notifications.append(str(text))
        else:
            self.notifications = [str(text)]

    def join_notifs(self):
        if self.notifications:
            return '\n'.join(self.notifications)
        else:
            return ''

    def check_filepath(self):
        path = self.config.get('path')
        if os.path.isfile(path):
            return True

    def import_msg(self):
        self.msg('Imported {0} models in {1}s, {2}ms.\n\n{3}'.format(len(self.chain), self.stats[0], self.stats[1], self.join_notifs()))

    def abort(self, text=None):
        if text:
            self.msg('Import aborted:\n{0}.'.format(text))
            sys.exit()
        self.msg('Import aborted.')
        sys.exit()

    def abort_checklog(self):
        path = self.xsi.InstallationPath(const.siUserAddonPath)
        path = os.path.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'import_log.log')
        if os.path.isfile(path):
            if self.msg('Encountered an error. Check {0} for more info.\nOpen log now?'.format(path), const.siMsgYesNo) == 6:
                os.startfile(path)
        else:
            self.msg('Encountered an error but cannot find log file.')
        sys.exit()

    def store_flags(self):
        andezetcore.save_settings('import', self.config)

    def import_(self):
        '''Prepares the import.'''
        self.store_flags()
        self.pb.set(1, 'Preparing...')
        self.pb.show()
        if not self.check_filepath():
            self.abort('File {0} does not exist..'.format(self.config.get('path')))
        self.pb.inc()
        self.do_import()
        self.import_msg()
        self.pb.hide()
        return

    def do_import(self):
        '''Actual import function.'''
        # Disable logging temporarily.
        print self.config.get('path')
        logging.info('==========================================')
        logging.info('Starting import at {0}.'.format(dt.now()))
        logging.info('.msh file path: {0}'.format(self.config.get('path')))
        prefs = self.xsi.Preferences
        originalcmd = prefs.GetPreferenceValue('scripting.cmdlog')
        originalins = prefs.GetPreferenceValue('Interaction.autoinspect')
        prefs.SetPreferenceValue('scripting.cmdlog', False)
        prefs.SetPreferenceValue('Interaction.autoinspect', False)
        # Cut path for better display.
        short_path = self.config.get('path').split('\\')
        short_path = short_path[-3], short_path[-2], short_path[-2], short_path[-1]
        short_path_fin = '...{0}'.format('\\'.join(short_path))
        self.pb.set(1, 'Unpacking {0}...'.format(short_path_fin))
        start = dt.now()
        unpacker_config = {'do_logging': self.config.get('log'),
                           'ignore_geo': self.config.get('ignoregeo'),
                           'triangulate': self.config.get('triangulate'),
                           'modulepath': os.path.join(self.xsi.InstallationPath(const.siUserAddonPath), 'XSIZETools\\Application\\Modules')}
        print self.config.get('path')
        unpacker = msh2_unpack.MSHUnpack(self.config.get('path'), unpacker_config)
        try:
            logging.info('Starting unpack.')
            self.msh = unpacker.unpack()
            logging.info('Finished unpack.')
        except (CRCError, msh2_unpack.UnpackError):
            logging.exception('')
            self.abort_checklog()
        self.pb.inc()
        if self.config.get('applyonly'):
            logging.info('Applyonly set, setting chain from selection.')
            if not self.xsi.Selection(0):
                self.abort('Aborted. No selection. Select the root of the hierarchy.')
            self.chain = self.get_all_children(self.xsi.Selection(0))
            logging.info('Selection item count: {0}, msh2 Model count: {1}.'.format(len(self.chain),
                                                                                    len(self.msh.models)))
        else:
            if not self.config.get('ignoregeo'):
                logging.info('Ignore Geo is unchecked, building with geo.')
                matbuilder = MaterialBuilder(self, self.msh)
                materials = matbuilder.build()
                builder = ChainBuilder(self, self.msh, materials)
            else:
                builder = ChainBuilder(self, self.msh)
            try:
                self.chain = builder.build()
            except MshImportError:
                logging.exception('')
                self.abort_checklog()
            enveloper = Enveloper(self, self.msh, self.chain)
            enveloper.envelope()
            if self.config.get('weld'):
                if not self.config.get('ignoregeo'):
                    for item in self.chain:
                        if not item.Type == 'polymsh':
                            continue
                        self.xsi.ApplyTopoOp('WeldEdges', item)
                        self.xsi.SetValue('{0}.polymsh.weldedgesop.distance'.format(item.Name), 0.02)
        if not self.msh.animation.empty and not self.config.get('ignoreanim'):
            anim = AnimationImport(self, self.chain, self.msh.animation.bones)
            anim.import_()
        if self.config.get('framerange'):
            scn = softimage.SIScene()
            pc = scn.get_playcontrol()
            pc.Parameters('In').Value = self.msh.info.frame_range[0]
            pc.Parameters('Out').Value = self.msh.info.frame_range[1]
        end = dt.now()
        res = end - start
        self.stats = res.seconds, res.microseconds
        # Enable logging.
        prefs.SetPreferenceValue('scripting.cmdlog', originalcmd)
        prefs.SetPreferenceValue('Interaction.autoinspect', originalins)
