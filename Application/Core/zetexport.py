'''
    Export.
'''

# TODO: FLGS:
#   - Hidden: |= 1
#   - DynamicallyLit |= 2
#   - RetainNormal |= 4
#   - RenderAfterShadows |= 8
#   - DontFlatten |= 16
#   - PS2Optimize |= 32


import softimage
import zetcore
import andecore
reload(zetcore)
reload(softimage)
reload(andecore)
import logging
reload(logging)
import sys
import os
from datetime import datetime
import msh2
reload(msh2)
from win32com.client import constants as const
from pythoncom import com_error
STR_CODEC = 'utf-8'


class BoneConverter(object):
    '''Converts an animated object to a msh2 bone.'''
    def __init__(self, si_mdl, anim, is_basepose):
        self.anim = anim
        self.mdl = si_mdl
        self.bone = msh2.Bone(self.anim.anim)
        self.is_basepose = is_basepose

    def convert(self):
        '''Gathers animation data for a bone.'''
        self.bone.name = self.mdl.Name.encode(STR_CODEC)
        self.bone.recrc()
        pos = []
        rot = []
        pc = self.anim.get_playcontrol()
        curr = pc.Parameters('Current').Value
        if self.is_basepose:
            tran = self.mdl.Kinematics.Local.GetTransform2(curr)
            pos.append((tran.PosX, tran.PosY, tran.PosZ))
            quat = tran.Rotation.Quaternion
            rot.append((quat.X, quat.Y, quat.Z, quat.W))
            tran = self.mdl.Kinematics.Local.GetTransform2(curr + 1)
            pos.append((tran.PosX, tran.PosY, tran.PosZ))
            quat = tran.Rotation.Quaternion
            rot.append((quat.X, quat.Y, quat.Z, quat.W))
            self.bone.pos_keyframes = pos
            self.bone.rot_keyframes = rot
            return self.bone

        for n in range(int(self.anim.anim.cycle.frames[0]), int(self.anim.anim.cycle.frames[1]) + 1):
            tran = self.mdl.Kinematics.Local.GetTransform2(n)
            pos.append((tran.PosX, tran.PosY, tran.PosZ))
            quat = tran.Rotation.Quaternion
            rot.append((quat.X, quat.Y, quat.Z, quat.W))
        self.bone.pos_keyframes = pos
        self.bone.rot_keyframes = rot
        return self.bone


class AnimationConverter(softimage.SIScene):
    '''Gathers animation for all objects and converts it into msh2 animation.'''
    def __init__(self, export):
        self.export = export
        self.anim = msh2.Animation(self.export.msh)

    def is_animated(self, bone):
        '''Check all relevant parameters if they are animated.'''
        if bone.posx.IsAnimated() or \
           bone.posy.IsAnimated() or \
           bone.posz.IsAnimated() or \
           bone.rotx.IsAnimated() or \
           bone.roty.IsAnimated() or \
           bone.rotz.IsAnimated() or \
           bone.sclx.IsAnimated() or \
           bone.scly.IsAnimated() or \
           bone.sclz.IsAnimated():
            return True
        return False

    def convert(self):
        '''Gathers animation data for all animated objects.'''
        self.export.pb.set(1, 'Preparing Animation...')
        cycle = msh2.Cycle(self.anim)
        pc = self.get_playcontrol()
        cycle.frames = pc.Parameters('In').Value, pc.Parameters('Out').Value
        self.anim.cycle = cycle
        bonecoll = msh2.BoneCollection(self.anim)
        basepose = self.export.ppg_params.get('basepose')
        nummodels = len(self.export.si_models)
        self.export.pb.inc()
        self.export.pb.set(nummodels, 'Iterating Models...')
        for index, model in enumerate(self.export.si_models):
            self.export.pb.setc('Analyzing {0}({1}/{2})'.format(model.Name,
                                                                index,
                                                                nummodels))
            # Originally this was used but it also reported constrained objects as animated: model.IsNodeAnimated()
            if self.is_animated(model):
                logging.info('Processing bone "%s".', model.Name)
                boneconv = BoneConverter(model, self, basepose)
                bonecoll.add(boneconv.convert())
                logging.info('Finished processing bone.')
                self.export.pb.setc('Building Bone {0}({1}/{2})'.format(model.Name,
                                                                        index,
                                                                        nummodels))
            self.export.pb.inc()
        self.anim.bones = bonecoll
        return self.anim


class SceneInfoConverter(softimage.SIScene):
    '''Converts general scene information into msh2 scene information.'''
    def __init__(self, export):
        self.export = export
        self.parent = None
        self.sinfo = msh2.SceneInfo(self.export.msh)

    def calculate_global_bbox(self):
        '''Calculates a global bounding box for all objects.'''
        from math import sqrt
        # GetBBox returns XYZ coordinates for the lower and upper bounds of
        # the bounding box.
        minx, miny, minz, maxx, maxy, maxz = self.export.xsi.GetBBox(self.export.si_models)
        # Add the positive values of every axis to get the distance between
        # the 2 points. Half them to get the extents from the center.
        width = (abs(minx) + abs(maxx)) / 2
        height = (abs(miny) + abs(maxy)) / 2
        depth = (abs(minz) + abs(maxz)) / 2
        # Now calculate the bounding sphere(encompass all points).
        radius = sqrt(width * width + height * height + depth * depth)
        # Now the center.
        cx = minx + (maxx - minx) / 2
        cy = miny + (maxy - miny) / 2
        cz = minz + (maxz - minz) / 2
        self.sinfo.bbox.extents = width, height, depth
        self.sinfo.bbox.radius = radius
        self.sinfo.bbox.center = cx, cy, cz

    def convert(self):
        '''Gathers the scene information.'''
        self.sinfo.name = self.get_name().encode(STR_CODEC) + '_ZETExported'
        # get the playcontrol object which contains frame range and fps.
        playcontrol = self.get_playcontrol()
        self.sinfo.frame_range = (playcontrol.Parameters('In').Value,
                                  playcontrol.Parameters('Out').Value)
        self.sinfo.fps = playcontrol.Parameters('Rate').Value
        self.calculate_global_bbox()
        return self.sinfo


class ModelConverter(softimage.SIModel):
    '''Converts a XSI polymsh to a msh2 mesh.'''
    def __init__(self, si_mdl, export, immediate_conversion=False):
        # Set some stuff.
        self.export = export
        self.si_model = si_mdl
        # Get geometry right at the beginning. It will be used often later.
        self.geo = si_mdl.ActivePrimitive.GetGeometry2(0)
        self.msh2_model = msh2.Model()
        self.msh2_model.msh = self.export.msh
        if immediate_conversion:
            self.convert()

    def get_short_name(self):
        return self.si_model.Name.split('.')[-1].encode(STR_CODEC)

    def is_shadow(self):
        '''Checks if this model is a shadow mesh.'''
        return 'shadow' in self.si_model.Name.lower()

    def is_collprim(self):
        '''Checks if this model is a collision primitive.'''
        if self.si_model.Name.lower().startswith('p_'):
            return True
        return False

    def is_cloth_collprim(self):
        '''Checks if this model is a cloth collision primitive.'''
        if self.si_model.Name.lower().startswith('c_'):
            return True
        return False

    def is_cloth(self):
        '''Checks if this model is a simulated cloth.'''
        if self.get_cloth_prop():
            return True
        return False

    def get_cloth_prop(self):
        '''Gets the cloth property of this model.'''
        for prop in self.si_model.Properties:
            if 'zecloth' in prop.Name.lower():
                return prop

    def get_msh2_model_type(self, model):
        '''Gets the msh2 model type, returns a string indicating the type.'''
        if model.Type in ('root', 'eff'):
            return 'null'
        elif model.Type == 'null':
            if self.export.model_deformers:
                if self.si_model.Name in self.export.model_deformers:
                    return 'bone'
            return 'null'
        elif model.Type == 'bone':
            return 'bone'
        elif model.Type == 'polymsh':
            # If its a poly mesh, check some other things.
            if self.is_cloth():
                return 'cloth'
            # Is it a bone with geometry?
            if 'bone' in model.Name:
                return 'geobone'
            elif self.is_weighted():
                return 'geodynamic'
            elif self.is_shadow():
                return 'geoshadow'
            else:
                return 'geostatic'
        elif model.Type == 'Texture Support':
            self.export.dontexport.append(model.Name)
            return 'null'
        else:
            self.export.abort('Object "{0}" has unsupported model type "{1}".'.format(model.Name, model.Type))

    def get_vertices(self):
        '''Creates a Vertex Collection and fills it with normals and positions,
        returns the collection.'''
        coll = msh2.VertexCollection()

        # Vertex positions in a one-dimensional array.
        # positions_and_normals = self.export.xsi.ZET_GetVertexPositionsWithNormals(self.geo, True)
        # n = 0
        # while n < len(positions_and_normals):
        #     position = positions_and_normals[n], positions_and_normals[n + 1], positions_and_normals[n + 2]
        #     normal = positions_and_normals[n + 3], positions_and_normals[n + 4], positions_and_normals[n + 5]
        #     n += 6
        #     coll.add(msh2.Vertex(position, normal))

        # Vertex positions in a one-dimensional array.
        vert_pos_list = self.export.xsi.CGA_GetNodeVertexPositions(self.geo, True)
        # Normal vectors in a one-dimensional array.
        normals_list = self.export.xsi.CGA_GetNodeNormals(self.geo)
        n = 0
        while n < len(vert_pos_list):
            coord = vert_pos_list[n], vert_pos_list[n + 1], vert_pos_list[n + 2]
            normal = normals_list[n], normals_list[n + 1], normals_list[n + 2]
            n += 3
            coll.add(msh2.Vertex(coord, normal))

        logging.info('Processed %s vertices.', len(coll))
        self.export.stats.verts += len(coll)
        return coll

    def get_uvs(self):
        '''Gets UV coordinates, returns a list of UV coordinate tuples.'''
        uv_list = self.export.xsi.ZET_GetUVs(self.geo, 0)
        uvs = []
        n = 0
        while n < len(uv_list):
            coord = uv_list[n], uv_list[n + 1]
            uvs.append(coord)
            # UVs are stored as UVWs in Softimage so ignore the W value.
            n += 3
        return uvs

    def set_vert_colors(self, vertex_collection):
        colors = self.export.xsi.CGA_GetVertexColors0(self.geo)

        for index, vertex in enumerate(vertex_collection):
            vertex.color = msh2.Color((colors[index * 4] * 255,
                                       colors[index * 4 + 1] * 255,
                                       colors[index * 4 + 2] * 255,
                                       colors[index * 4 + 3] * 255,
                                      ))


    def get_vert_colors(self):
        '''Gets RGBA vertex colors, returns them as a Color object.'''
        col_list = self.export.xsi.CGA_GetVertexColors0(self.geo)
        colors = []
        n = 0
        while n < len(col_list):
            color = msh2.Color((col_list[n] * 255,
                                col_list[n + 1] * 255,
                                col_list[n + 2] * 255,
                                col_list[n + 3] * 255))
            colors.append(color)
            n += 4
        return colors

    def set_weights(self, vertex_collection):
        weights, deformer_names = self.export.xsi.ZET_GetWeights(self.geo)

        logging.debug('# of verts: %s, # of weights: %s', len(vertex_collection), len(weights) / len(deformer_names))

        for n in xrange(len(weights) / len(deformer_names)):
            vertex = vertex_collection[n]

            weight_values = [.0] * 4
            deformers = [''] * 4
            deformer_indices = [0] * 4

            number_of_deformers = 0
            for index, deformer in enumerate(deformer_names):
                if weights[n * 3 + index] > 0 and number_of_deformers < 4:
                    weight_values[number_of_deformers] = weights[n * 3 + index] / 100
                    deformers[number_of_deformers] = deformer
                    deformer_indices[number_of_deformers] = index
                    number_of_deformers += 1

            vertex.weights = weight_values
            vertex.deformers = deformers
            vertex.deformer_indices = deformer_indices
        

    def get_weights(self):
        '''Gets weights and deformers, returns a list of four weight value
        tuples and four deformer names tuples.'''
        _, weight_list, def_list = self.export.xsi.CGA_GetWeightsZE(self.geo)

        # Nodes per point: point 0: node_index, point 1: node_index etc...
        nodes_per_point = self.export.xsi.CGA_GetNodesPerPoint(self.geo)

        # Temporary lists.
        weights_temp = []
        deformers_temp = []
        deformer_indices_temp = []

        for chunk in andecore.chunks(weight_list, len(def_list)):
            weight_index_pairs = [[weight / 100, i] for i, weight in enumerate(chunk) if weight > 0.01]

            weight_index_pairs.sort(key=lambda p: p[0], reverse=True)

            # ZE only supports 4 deformers.
            used_pairs = weight_index_pairs[:4]

            total_weight = sum([w for w, _ in used_pairs])

            # Ensure weights sum up to 1 (100%).
            for p in used_pairs:
                p[0] = p[0] / total_weight

            used_pairs += [(0, 0)] * max(0, 4 - len(used_pairs))
            
            weights_temp.append([weight for weight, _ in used_pairs])
            deformers_temp.append([def_list[i] for _, i in used_pairs])
            deformer_indices_temp.append([i for _, i in used_pairs])

        weights = len(nodes_per_point) * ['empty']
        deformers = len(nodes_per_point) * ['empty']
        deformer_indices = len(nodes_per_point) * ['empty']

        for ndx, el in enumerate(nodes_per_point):
            weights[ndx] = weights_temp[el]
            deformers[ndx] = deformers_temp[el]
            deformer_indices[ndx] = deformer_indices_temp[el]

        return weights, deformers, deformer_indices

    def get_deformers(self):
        '''Gets a lost fof all deformers for this model.'''
        _, deformers = self.export.xsi.ZET_GetWeights(self.geo)
        return [deformer.encode(STR_CODEC) for deformer in deformers]

    def get_faces(self):
        '''Creates a FaceCollection and fills it with Faces, returns the
        collection.'''
        coll = msh2.FaceCollection()
        # node_indices, vert_count = self.export.xsi.ZET_GetPolyVertexIndicesAndCounts(self.geo)
        node_indices = self.export.xsi.CGA_GetNodeIndices(self.geo)
        vert_count = self.export.xsi.CGA_GetPolygonVerticesCount(self.geo)
        fc = 0
        for el in vert_count:
            face = msh2.Face()
            face.vertices = []
            for n in xrange(el):
                face.vertices.append(node_indices[fc + n])
            if el == 4:
                p2 = face.vertices[2]
                face.vertices[2] = face.vertices[3]
                face.vertices[3] = p2
            elif el == 5:
                p2 = face.vertices[2]
                face.vertices[2] = face.vertices[3]
                face.vertices[3] = p2
            fc += el
            coll.add(face)
        logging.info('Processed %s faces.', len(coll))
        self.export.stats.faces += len(coll)
        return coll

    def process_geometry(self):
        '''Processes the SI polymsh geometry into one segment and returns it.'''
        seg = msh2.SegmentGeometry()
        seg.mat_name = self.export.get_main_material_name(self.si_model)
        seg.material = self.export.msh.get_mat_by_name(seg.mat_name)
        seg.vertices = self.get_vertices()
        seg.vertices.segment = seg
        seg.faces = self.get_faces()
        seg.faces.segment = seg
        if self.is_uved():
            seg.vertices.uved = True
            seg.vertices.set_uvs(self.get_uvs())
        if self.is_colored():
            seg.vertices.colored = True
            self.set_vert_colors(seg.vertices)
            # seg.vertices.set_colors(self.get_vert_colors())
        if self.is_weighted():
            seg.vertices.weighted = True
            # self.set_weights(seg.vertices)
            seg.vertices.set_weights(*self.get_weights())
        return seg

    def clear_multiverts(self, collection):
        '''Removes vertices that have the same position, normals and UVs.'''
        with zetcore.Timer('Cleared multiverts in %ss %sms.'):
            for segment in collection:
                if isinstance(segment, msh2.SegmentGeometry):
                    segment.clear_doubles()

    def get_segments(self):
        '''Creates segments from the main geometry and returns them in
        a SegmentCollection.'''
        # First get the geometry for the complete mesh.
        geometry = self.process_geometry()
        coll = msh2.SegmentCollection(self.msh2_model)
        coll.model = self.msh2_model
        coll.msh = self.msh2_model.msh
        geometry.collection = coll
        # Then split it up into chunks for more than one material per model.
        poly_mat_indices = self.export.xsi.ZET_GetPolyMaterialIndices(self.geo)
        mat_names = self.export.xsi.ZET_GetMaterialNames(self.geo)
        coll.add(geometry)
        # If the model only has one material just export this one chunk.
        if len(mat_names) == 1:
            self.clear_multiverts(coll)
            return coll
        # Otherwise split the geometry.
        coll.split(0, poly_mat_indices, mat_names)
        coll.assign_materials(self.export.msh.materials)

        self.clear_multiverts(coll)
        return coll
    
    def get_shadow_segments(self):
        seg = msh2.ShadowGeometry()

        # Positions
        flat_positions = self.export.xsi.ZET_GetVertexPositions(self.geo, True)

        seg.positions = [flat_positions[n:n+3] for n in xrange(0, len(flat_positions), 3)]

        # Faces as half-edges
        vert_indices, vert_counts = self.export.xsi.ZET_GetPolyVertexIndicesAndCounts(self.geo)

        self.export.stats.verts += len(seg.positions)
        self.export.stats.faces += len(vert_counts)

        # Keeps track of all edge indices for an undirected edge (vert_index, next_vert_index)
        edge_dict = {}

        # Half-edges
        edges = []

        vert_count_offset = 0

        for vert_count in vert_counts:
            for n in xrange(vert_count):
                vert_index = vert_indices[vert_count_offset + n]

                # Wrap around if last in face, otherwise just next edge index
                next_edge_index = len(edges) - n if n == vert_count - 1 else len(edges) + 1

                edge = msh2.ShadowGeometryEdge(vert_index, next_edge_index, -1)

                next_vert_index = vert_indices[vert_count_offset + ((n + 1) % vert_count)]

                # Always store as (smaller index, larger index) for easier lookup
                edge_key = (min(vert_index, next_vert_index), max(vert_index, next_vert_index))

                edge_indices = edge_dict.get(edge_key)

                if not edge_indices:
                    edge_dict[edge_key] = [len(edges)]
                else:
                    edge_indices.append(len(edges))

                edges.append(edge)

            vert_count_offset += vert_count

        for key, indices in edge_dict.items():
            if len(indices) == 2:
                edge_index_1 = indices[0]
                edge_index_2 = indices[1]

                edges[edge_index_1].opposite_edge_index = edge_index_2
                edges[edge_index_2].opposite_edge_index = edge_index_1
            else:
                logging.warning('Expected 2 edges for key {0}, got {1}. Shadow meshes should always be closed.'.format(key, len(indices)))

        seg.edges = edges

        coll = msh2.SegmentCollection(self.msh2_model)
        coll.model = self.msh2_model
        coll.msh = self.msh2_model.msh
        seg.collection = coll
        coll.add(seg)

        return coll

    def process_bbox(self):
        '''Calculates a bounding box for this model.'''
        bbox = self.geo.GetBoundingBox(self.si_model.Kinematics.Local.Transform)
        bsphere = self.geo.GetBoundingSphere(const.siVolumeCenterMethodBBoxCenter,
                                             self.si_model.Kinematics.Local.Transform)
        self.msh2_model.bbox.extents = (bbox[3] / 2 * self.msh2_model.transform.scale[0],
                                        bbox[4] / 2 * self.msh2_model.transform.scale[1],
                                        bbox[5] / 2 * self.msh2_model.transform.scale[2])
        self.msh2_model.bbox.center = bbox[0], bbox[1], bbox[2]
        self.msh2_model.bbox.radius = bsphere[3]

    def process_c_collision_primitive(self):
        '''Processes cloth collision primitive data for this model.'''
        logging.info('Processing cloth collision primitive.')
        self.msh2_model.cloth_collprim = True

        sm = self.si_model
        mm = self.msh2_model
        try:
            radius = self.export.xsi.GetValue('{0}.polymsh.geom.sphere.radius'.format(sm.FullName)) * mm.transform.scale[0]
            mm.primitive = (0, radius, radius, radius)
        except com_error:
            try:
                radius = self.export.xsi.GetValue('{0}.polymsh.geom.cylinder.radius'.format(sm.FullName)) * mm.transform.scale[0]
                height = self.export.xsi.GetValue('{0}.polymsh.geom.cylinder.height'.format(sm.FullName)) * mm.transform.scale[0]
                mm.primitive = (1, radius, height, 0)
            except com_error:
                try:
                    length = self.export.xsi.GetValue('{0}.polymsh.geom.cube.length'.format(sm.FullName))
                    mm.primitive = (2, length * mm.transform.scale[0] * .5, length * mm.transform.scale[1] * .5, length * mm.transform.scale[2] * .5)
                except com_error:
                    self.msh2_model.cloth_collprim = False
                    self.export.abort('Could not find valid Primitive (sphere/cube/cylinder) for Cloth Collision Primitive "{0}".'.format(sm.Name))
                    return
        mm.transform.scale = 1.0, 1.0, 1.0

    def process_collision_prim(self):
        '''Processes collision primitive data for this model.'''
        self.msh2_model.collprim = True
        sm = self.si_model
        mm = self.msh2_model
        if sm.Parent:
            parent_transform = sm.Parent.Kinematics.Local.Transform
        else:
            parent_transform = self.export.xsi.ActiveSceneRoot.Kinematics.Local.Transform
        try:
            radius = self.export.xsi.GetValue('{0}.polymsh.geom.sphere.radius'.format(sm.FullName))
            mm.primitive = (0, radius, radius, radius)
        except com_error:
            try:
                radius = self.export.xsi.GetValue('{0}.polymsh.geom.cylinder.radius'.format(sm.FullName))
                height = self.export.xsi.GetValue('{0}.polymsh.geom.cylinder.height'.format(sm.FullName))
                mm.primitive = (2, radius, height, 0)
            except com_error:
                try:
                    length = self.export.xsi.GetValue('{0}.polymsh.geom.cube.length'.format(sm.FullName))
                    mm.primitive = (4, length * mm.transform.scale[0] * .5 * parent_transform.SclX,
                                       length * mm.transform.scale[1] * .5 * parent_transform.SclY,
                                       length * mm.transform.scale[2] * .5 * parent_transform.SclZ)
                except com_error:
                    self.msh2_model.cloth_collprim = False
                    self.export.abort('Could not find valid Primitive (sphere/cube/cylinder) for Collision Primitive "{0}".'.format(sm.Name))
                    return
        mm.transform.scale = 1.0, 1.0, 1.0

    def get_fixed(self):
        '''Get the elements of the fixed points cluster.'''
        for cls in self.geo.Clusters:
            if 'ZEFixed' in cls.Name:
                return cls.Elements.Array
        return []

    def get_cloth_weights(self):
        '''Get weights for all fixed points.'''
        for cls in self.geo.Clusters.Filter('pnt'):
            for prop in cls.Properties:
                if prop.Type == 'envweights':
                    weights = prop.Elements.Array
        ret_weights = []
        for n in xrange(len(weights[0])):
            for i in xrange(len(weights)):
                if weights[i][n] > 49.0:
                    ret_weights.append(i)
                    break
        return ret_weights

    def get_cloth_deformers(self):
        '''Get all deformers for cloth.'''
        env = self.si_model.Envelopes(0)
        defs = []
        for deformer in env.Deformers:
            defs.append(deformer.Name)
        return defs

    def get_cloth_geo(self):
        '''Gather the geometry for cloth.'''
        facecoll = msh2.FaceCollection()
        vertcoll = msh2.ClothVertexCollection()
        if not self.is_uved():
            self.export.abort('{0} doesnt have UVs(necessary for Cloth).'.format(self.si_model.Name))
        fixed = self.get_fixed()
        # Two dimensional: [0][0] = first deformer, weight for first point in cluster.
        #                  [1][0] = second deformer, first point.
        #                  [2][2] = third deformer, third point in cluster.
        weights = [0] * self.geo.Points.Count
        # One dimensional.
        deformers = ['']
        if self.is_weighted():
            weights = self.get_cloth_weights()
            deformers = self.get_cloth_deformers()
            logging.info('Retrieved cloth deformers: %s (%s)', deformers, len(deformers))

        vertex_indices, poly_lengths = self.export.xsi.ZET_GetPolyVertexIndicesAndCounts(self.geo)

        offset = 0
        for poly_length in poly_lengths:
            face = msh2.Face(vertex_indices[offset:offset + poly_length])
            offset += poly_length
            facecoll.add(face)

        positions = self.export.xsi.ZET_GetVertexPositions(self.geo, False)
        vertex_to_node_indices = self.export.xsi.ZET_GetVertexToNodeIndices(self.geo)
        uvs = self.export.xsi.ZET_GetUVs(self.geo, 0)
        
        for n in xrange(len(vertex_to_node_indices)):
            vert = msh2.ClothVertex((positions[n * 3],
                                     positions[n * 3 + 1],
                                     positions[n * 3 + 2],))
            node_index = vertex_to_node_indices[n]
            vert.uv = uvs[node_index * 3], uvs[node_index * 3 + 1]
            if n in fixed:
                vert.is_fixed = True
            vert.deformer = deformers[weights[n]].encode(STR_CODEC)
            vertcoll.add(vert)
        logging.info('Processed %s vertices.', len(vertcoll))
        return facecoll, vertcoll

    def get_cloth_tex(self):
        '''Get texture name for cloth.'''
        for ps in self.si_model.Properties:
            if 'ZEC' in ps.Name:
                return ps.Parameters('texture').Value.encode(STR_CODEC)

    def get_cloth_collisions(self, geo):
        '''Gather all cloth collisions for this model.'''
        collision_names = []
        collisions = []
        for ps in self.si_model.Properties:
            if 'ZEC' in ps.Name:
                collision_names = ps.Parameters('collisions').Value
                if collision_names:
                    collision_names = collision_names.encode(STR_CODEC).split(',')
                break
        for collision_name in collision_names:
            # Split name by periods to remove possible Softimage Model names (ie MyModel.MyObject).
            short_collision_name = collision_name.encode(STR_CODEC)
            if '.' in short_collision_name:
                short_collision_name = short_collision_name.split('.')[-1]
            if not short_collision_name.lower().startswith('c_'):
                self.export.abort('Cloth collision names should start with "c_" ({0}).'.format(short_collision_name))
            collision = msh2.ClothCollision(geo)
            collision.name = short_collision_name
            try:
                collision.parent = self.export.xsi.Dictionary.GetObject(collision_name, False).Parent.Name.encode(STR_CODEC)
            except AttributeError as e:
                logging.exception(e)
                self.export.abort('Could not find cloth collision "{0}" for "{1}".'.format(collision_name, self.msh2_model.name))
            collisions.append(collision)
        return collisions

    def get_cloth(self):
        '''Get the cloth data for this model.'''
        coll = msh2.SegmentCollection(self.msh2_model)
        clothgeo = msh2.ClothGeometry(coll)
        with zetcore.Timer('Cloth geometry in %ss %sms.'):
            clothgeo.faces, clothgeo.vertices = self.get_cloth_geo()
        clothgeo.assign_parents()
        clothgeo.texture = self.get_cloth_tex()
        with zetcore.Timer('Cloth constraints in %ss %sms.'):
            clothgeo.create_constraints()

        with zetcore.Timer('Cloth collisions in %ss %sms.'):
            clothgeo.collisions = self.get_cloth_collisions(clothgeo)

        coll.add(clothgeo)
        return coll

    def convert(self):
        '''Converts the SI model into a msh2 model, accessible via
        ModelConverter.msh2_model.'''
        # I'm using strings to store relationships and deformers because I might not
        # know every model yet and so I cant reference it.
        self.msh2_model.name = self.get_short_name()
        # Check if the model is the root(selected) model. If it is, ignore it's parent.
        if self.si_model != self.export.si_root:
            self.msh2_model.parent_name = self.si_model.Parent.Name.encode(STR_CODEC)
        # 1 = hidden, 0 = not hidden, so cast the bool to an int and reverse it.
        self.msh2_model.vis = int(not self.get_vis(self.si_model))
        self.msh2_model.transform = msh2.Transform(*self.get_transform_quat(self.si_model))
        self.msh2_model.model_type = self.get_msh2_model_type(self.si_model)
        if self.msh2_model.model_type == 'geoshadow':
            logging.info('Is shadow.')
            with zetcore.Timer('Shadow segments in %ss %sms.'):
                self.msh2_model.segments = self.get_shadow_segments()
            self.process_bbox()
        elif 'geo' in self.msh2_model.model_type:
            logging.info('Is geometry.')
            self.msh2_model.segments = None
            with zetcore.Timer('Segments in %ss %sms.'):
                self.msh2_model.segments = self.get_segments()
            self.process_bbox()
        if self.msh2_model.model_type == 'cloth':
            logging.info('Is cloth.')
            self.msh2_model.segments = None
            with zetcore.Timer('Cloth Segment in %ss %sms.'):
                self.msh2_model.segments = self.get_cloth()
            if self.is_weighted():
                self.msh2_model.deformers = self.get_deformers()
                self.export.add_deformers(self.msh2_model.deformers)
        if self.msh2_model.model_type == 'geodynamic':
            logging.info('Is geodynamic.')
            self.msh2_model.deformers = self.get_deformers()
            self.export.add_deformers(self.msh2_model.deformers)
        if self.is_collprim():
            logging.info('Is collision primitive.')
            with zetcore.Timer('CollPrim in %ss %sms.'):
                self.process_collision_prim()
        elif self.is_cloth_collprim():
            logging.info('Is cloth collision primitive.')
            with zetcore.Timer('ClothCollPrim in %ss %sms.'):
                self.process_c_collision_primitive()
        # Reset scale because we're using vertex world coordinates.
        # And do it after process_collision_prim because it needs the scale.
        self.msh2_model.transform.scale = 1.0, 1.0, 1.0

        return self.msh2_model


class MaterialConverter(softimage.SIMaterial):
    '''Converts a XSI Material to a msh2 material.'''
    def __init__(self, si_mat, export, index, immediate_conversion=False):
        self.export = export
        self.si_material = si_mat
        self.msh2_material = msh2.Material()
        self.msh2_material.index = index
        if immediate_conversion:
            self.convert()

    def get_mat_prop(self):
        '''Returns the material property if it can find it.'''
        # Retrieves the material property containing ZE specific data.
        for prop in self.si_material.Properties:
            if 'ZeroEngine' in prop.Name:
                return prop

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

    def process_shader_data(self):
        '''Gets data like color, texture and glossyness from the shader.'''
        for shader in self.si_material.Shaders:
            # First get the diffuse parameter of the shader(diffuse input)
            diff_param = shader.Parameters('diffuse')
            # If the parameter has a source(a connection to something)
            if diff_param.Source:
                # This is some sort of hack. Gives me access to the Image.
                diff_src_img = diff_param.Source.Parent
                # Get the image clip of the image. Image Clips holds File name etc.
                # Image only holds image data(pixels, width etc).
                clip = diff_src_img.ImageClips(0)
                # Then get the clip source(texture).
                self.msh2_material.tex0 = self.get_clip_source_name(clip)
            try:
                self.msh2_material.diff_color = msh2.Color(self.get_shader_color(shader, 'diffuse'))
                self.msh2_material.diff_color.alpha = 1.0
                self.msh2_material.ambt_color = msh2.Color(self.get_shader_color(shader, 'ambient'))
                self.msh2_material.ambt_color.alpha = 1.0
            except AttributeError as ae:
                self.export.abort(str(ae) + '\nMaterial {0} is not of type Phong or Lambert.'.format(self.si_material.name))
            try:
                self.msh2_material.spec_color = msh2.Color(self.get_shader_color(shader, 'specular'))
                self.msh2_material.spec_color.alpha = 1.0
                self.msh2_material.gloss = shader.Parameters('shiny').Value
            except AttributeError as ae:
                self.msh2_material.spec_color = msh2.Color((0.0, 0.0, 0.0, 1.0))
                self.msh2_material.gloss = 0
        return True

    def process_msh_material_data(self, prop):
        '''Retrieves MSH material flags.'''
        # Add all flag values.
        # Thats faster than looping through them with ifs.
        # Even if we have to decode that int later.
        value = 0
        value += int(prop.emissive.Value)
        value += 2 * int(prop.glow.Value)
        value += 4 * int(prop.transparency.Value)
        value += 16 * int(prop.hardedged.Value)
        value += 32 * int(prop.perpixel.Value)
        value += 64 * int(prop.additive.Value)
        value += 128 * int(prop.specular.Value)
        # Decode the value.
        self.msh2_material.flags = self.flags_from_int(value)
        # Get some misc values from the property.
        self.msh2_material.render_type = prop.rendertype.Value
        self.msh2_material.data0 = prop.data0.Value
        self.msh2_material.data1 = prop.data1.Value
        self.msh2_material.tex1 = prop.tex1.Value.encode(STR_CODEC)
        self.msh2_material.tex2 = prop.tex2.Value.encode(STR_CODEC)
        self.msh2_material.tex3 = prop.tex3.Value.encode(STR_CODEC)

    def convert(self):
        '''Converts the XSI material to a msh2 material, accessible via
        MaterialConverter.msh2_material.'''
        # First get the material property
        self.msh2_material.name = self.si_material.Name.encode(STR_CODEC)
        self.process_shader_data()
        prop = self.get_mat_prop()
        if prop:
            self.process_msh_material_data(prop)
        return self.msh2_material


# Inherit from SIGeneral which contains general functions
#  for working with XSI.
class Export(softimage.SIGeneral):
    '''Main export class. Handles selection and data.'''
    def __init__(self, app, config=None):
        self.xsi = app
        self.ADDONPATH = self.xsi.InstallationPath(const.siUserAddonPath)
        self.notifications = None
        self.model_deformers = None
        self.stats = zetcore.ExportStats()
        self.dontexport = []
        # pb = progress bar
        self.pb = softimage.SIProgressBar()
        if config:
            self.ppg_params = config
        else:
            return
            self.ppg_params = zetcore.load_settings('export', PPG.Inspected(0))
        logpath = os.path.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'export_log.log')
        logging.basicConfig(format='%(levelname)s (%(lineno)d, %(funcName)s): %(message)s',
                            filename=logpath,
                            filemode='w',
                            level=logging.DEBUG)

    def export_msg(self):
        '''Displays a message after export.'''
        if not self.ppg_params.get('show_finished_dialog'):
            return
        notifs = ['\n\n']
        if self.notifications:
            for notif in self.notifications:
                notifs.append(notif)
                notifs.append('\n')
        self.msg('Exported {0} materials and {1} models with {2} verts and {3} faces in {4} seconds and {5} microseconds.{6}'.format(self.stats.mats,
                                                                                                                                     self.stats.models,
                                                                                                                                     self.stats.verts,
                                                                                                                                     self.stats.faces,
                                                                                                                                     self.stats.secs(),
                                                                                                                                     self.stats.micros(),
                                                                                                                                     ''.join(notifs)))

    def log(self, text):
        self.export_log.append(text)

    def log_hier(self):
        text = ['Hierarchy:\n']
        for mdl in self.msh.models:
            text.append('\t{0}\n'.format(mdl.name))
        self.msg(''.join(text))

    def notify(self, text):
        '''Adds a notification to the after-export message.'''
        if self.notifications:
            self.notifications.append(text)
        else:
            self.notifications = [text]

    def add_deformers(self, defs):
        if self.model_deformers:
            for deformer in defs:
                if deformer not in self.model_deformers:
                    self.model_deformers.append(deformer)
        else:
            self.model_deformers = defs

    def abort(self, text=''):
        '''Aborts the export with an optional text message.'''
        if text:
            self.msg('Export aborted:\n{0}.'.format(text))
            sys.exit()
        self.msg('Export aborted.')
        sys.exit()

    def check_filepath(self):
        '''Checks if the filepath exists and if there is a file. Asks to
        overwrite the file.'''
        path = self.ppg_params.get('path')
        if bool(self.ppg_params.get('rootname')):
            splitpath = path.split('\\')
            splitpath[-1] = self.si_root.Name.encode(STR_CODEC) + '.msh'
            path = '\\'.join(splitpath)
        filepath = ''
        splitpath = path.split('\\')
        filepath_items = ['...', splitpath[-3], splitpath[-2], splitpath[-1]]
        filepath = '\\'.join(filepath_items)
        if os.path.isfile(path) and not self.ppg_params.get('overwrite'):
            if self.msg('{0} already exists, overwrite?'.format(filepath), const.siMsgYesNo) != 6:
                self.abort()

    def export(self):
        '''Prepares export.'''
        self.stats.start = datetime.now()
        self.pb.inc()
        zetcore.save_settings('export', self.ppg_params)
        self.si_root = self.xsi.Selection(0)
        if not self.si_root:
            self.abort('No models selected.')
        if self.ppg_params.get('batch'):
            direct_children = self.si_root.Children
            for child in direct_children:
                self.si_root = child
                self.si_models = self.get_all_children(child)
                self.si_materials = self.unique_materials(self.si_models)
                self.do_export()
            self.stats.end = datetime.now()
            self.export_msg()
            return
        self.si_models = self.get_all_children(self.si_root)
        self.si_materials = self.unique_materials(self.si_models)
        self.do_export()
        self.stats.end = datetime.now()
        self.export_msg()
        return

    def do_export(self):
        '''Main export routine. Exports and writes a .msh file.'''
        self.check_filepath()
        logging.info('==========================================')
        logging.info('Starting export at {0}.'.format(datetime.now()))
        logging.info('.msh file path: {0}'.format(self.ppg_params.get('path')))
        self.msh = None
        self.msh = msh2.Msh()

        # Convert materials from XSI to msh2.
        self.pb.set(len(self.si_materials), 'Processing materials...')
        self.pb.show()
        self.msh.materials = msh2.MaterialCollection(self.msh)
        self.msh.materials.replace([])
        with zetcore.Timer('Materials in %ss %sms.'):
            for ndx, material in enumerate(self.si_materials):
                logging.info('Processing material "{0}".'.format(material.Name))
                self.pb.setc('Processing Material {0}... {1}/{2}'.format(material.Name,
                                                                         ndx + 1,
                                                                         len(self.si_materials)))
                conv = MaterialConverter(material, self, ndx)
                self.msh.materials.add(conv.convert())
                logging.info('Finished processing.')
                self.pb.inc()
            self.msh.materials.assign_indices()
        self.stats.mats += len(self.msh.materials)

        # Now Models.
        self.pb.set(len(self.si_models), 'Processing models...')
        self.msh.models = None
        self.msh.models = msh2.ModelCollection(self.msh)
        self.msh.models.replace([])
        with zetcore.Timer('Models in %ss %sms.'):
            for ndx, model in enumerate(self.si_models):
                self.pb.setc('Processing Model {0}... {1}/{2}'.format(model.Name,
                                                                      ndx + 1,
                                                                      len(self.si_models)))
                logging.info('Processing model "{0}".'.format(model.Name))
                with zetcore.Timer('Model in %ss %sms.'):
                    conv = ModelConverter(model, self)
                    self.msh.models.add(conv.convert())
                logging.info('Finished processing.')
                self.pb.inc()
            self.msh.models.assign_indices()
            self.msh.models.assign_parents()

        self.msh.models.remove_multi(self.dontexport)

        with zetcore.Timer('Assigned cloth collisions in %ss %sms.'):
            self.msh.models.assign_cloth_collisions()
        self.stats.models += len(self.msh.models)

        # Scene Info.
        self.pb.set(1, 'Getting Scene Info...')
        logging.info('Processing Scene Info.')
        scnnfo = SceneInfoConverter(self)
        scnnfo.parent = self.msh
        self.msh.info = scnnfo.convert()
        logging.info('Finished processing Scene Info.')
        self.pb.inc()

        # Animation.
        self.pb.set(2, 'Processing Animation...')
        with zetcore.Timer('Processed animation in %ss %sms.'):
            if self.ppg_params.get('anim'):
                logging.info('Processing animation.')
                anim = AnimationConverter(self)
                self.msh.animation = anim.convert()
            else:
                logging.info('Setting empty animation.')
                self.msh.animation = msh2.Animation(None, 'empty')
        self.pb.inc()
        # Make nulls which are used as envelopes bones.
        if self.model_deformers:
            logging.info('Setting model type to "bone" for {0}.'.format(self.model_deformers))
            for mdl in self.msh.models:
                if mdl.name in self.model_deformers:
                    mdl.model_type = 'bone'
        self.pb.inc()

        if not self.write_msh(self.msh.pack()):
            self.msg('Failed {0}.'.format(self.si_root.Name))

    def write_msh(self, data):
        path = self.ppg_params.get('path')
        if bool(self.ppg_params.get('rootname')):
            splitpath = path.split('\\')
            splitpath[-1] = self.si_root.Name.encode(STR_CODEC) + '.msh'
            path = '\\'.join(splitpath)
        try:
            with open(path, 'wb') as fh:
                fh.write(data)
            return True
        except IOError as ioe:
            self.msg(str(ioe))
            return False
