#########################################################
#####                 andesicore                    #####
#####                                               #####
#####             XSI utility classes               #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################
from win32com.client import constants as const
import win32com
STR_CODEC = 'utf-8'
xsi = win32com.client.Dispatch('XSI.Application')
xsiui = win32com.client.Dispatch('XSI.UIToolkit')
xsimath = win32com.client.Dispatch('XSI.Math')


class SIScene(object):
    def get_playcontrol(self):
        return xsi.Dictionary.GetObject('PlayControl')

    def get_name(self):
        return xsi.ActiveProject.ActiveScene.Name

    def wirecol(self, r, g, b):
        wr = int(round(r * 7)) << 1
        wg = int(round(g * 7)) << 4
        wb = int(round(b * 7)) << 7
        return wr + wg + wb


class SIModel(object):
    def __init__(self, si_model):
        self.si_model = si_model
        self.geo = si_model.ActivePrimitive.GetGeometry2(0)

    def get_uv_props(self):
        cls = self.si_model.ActivePrimitive.GetGeometry2(0).Clusters
        sample = cls.Filter('sample')
        for cls in sample:
            props = cls.Properties.Filter('uvspace')
            return props

    def get_envelope_props(self):
        pnt_clusters = self.geo.Clusters.Filter('pnt')
        for cluster in pnt_clusters:
            properties = cluster.Properties
            weight_props = properties.Filter('envweights')
            return weight_props

    def get_vertex_color_props(self):
        cls = self.si_model.ActivePrimitive.GetGeometry2(0).Clusters
        sample = cls.Filter('sample')
        for cls in sample:
            props = cls.Properties.Filter('vertexcolor')
            return props

    def set_weights(self, index, weights):
        prop = self.get_envelope_props()[index]
        prop.Elements.Array = weights
        return True

    def set_uvs(self, index, uvs):
        prop = self.get_uv_props()[index]
        prop.Elements.Array = uvs
        return True

    def set_vertex_colors(self, index, colors):
        prop = self.get_vertex_color_props()[index]
        prop.Elements.Array = colors
        return True

    def get_vis(self, model):
        vis = model.Properties.Filter('visibility')
        prop = vis[0]
        val = prop.viewvis.Value
        if val:
            return True
        return False

    def get_transform_quat(self, model):
        transform = model.Kinematics.Local.Transform
        quat = xsimath.CreateQuaternion()
        transform.GetRotationQuaternion(quat)
        sca = transform.SclX, transform.SclY, transform.SclZ
        rot = quat.X, quat.Y, quat.Z, quat.W
        tra = transform.PosX, transform.PosY, transform.PosZ
        return tra, rot, sca

    def is_uved(self):
        sample_clusters = self.geo.Clusters.Filter('sample')
        for cls in sample_clusters:
            props = cls.Properties
            uv_props = props.Filter('uvspace')
            if uv_props.Count > 0:
                return True

    def is_colored(self):
        sample_clusters = self.geo.Clusters.Filter('sample')
        for cls in sample_clusters:
            props = cls.Properties
            vcol_props = props.Filter('vertexcolor')
            if vcol_props.Count > 0:
                return True

    def is_weighted(self):
        pnt_clusters = self.geo.Clusters.Filter('pnt')
        for cluster in pnt_clusters:
            properties = cluster.Properties
            weight_props = properties.Filter('envweights')
            if weight_props.Count > 0:
                return True


class SIMaterial(object):
    def get_clip_source_name(self, clip):
        src = clip.Source
        filename = src.Parameters('FileName').Value
        filename_list = filename.split('\\')
        return filename_list[-1].encode(STR_CODEC)

    def get_shader_color(self, shader, color):
        col = shader.Parameters(color).Value
        return col.Red, col.Green, col.Blue, col.Alpha


class SIGeneral(object):
    def get_objects_by_name(self, modelnames):
        models = []
        for name in modelnames:
            xsifact = win32com.client.Dispatch('XSI.Factory')
            collection = xsifact.CreateObject('XSI.Collection')
            collection.items = name
            models.append(collection(0))
        return models

    def msg(self, message, msg_type=const.siMsgOkOnly, plugin='XSIZETools'):
        return xsiui.MsgBox(message, msg_type, plugin)

    def get_obj_by_name(self, name):
        xsifact = win32com.client.Dispatch('XSI.Factory')
        collection = xsifact.CreateObject('XSI.Collection')
        collection.items = name
        if collection.count == 1:
            return collection(0)

    def check_existence(self, name):
        xsifact = win32com.client.Dispatch('XSI.Factory')
        collection = xsifact.CreateObject('XSI.Collection')
        collection.items = name
        return collection.Count

    def get_main_material_name(self, obj):
        if obj.Material:
            return obj.Material.Name
        return 'Scene_Material'

    def get_all_children(self, root):
        if root:
            return self._get_all_children(root)
        else:
            return None

    def _get_all_children(self, root):
        '''Recursively adds children to a list.'''
        children = []
        children.append(root)
        if root.Children(0):
            chldrn = list(root.Children)
            for child in chldrn:
                children.extend(self.get_all_children(child))
        return children

    def unique_materials(self, obj_list):
        materials = self.all_materials(obj_list)
        unique = []
        unique_names = []
        for mat in materials:
            if mat.Name not in unique_names:
                unique.append(mat)
                unique_names.append(mat.Name)
        return unique

    def all_materials(self, obj_list):
        materials = []
        for obj in obj_list:
            # Non-polymsh objects sometimes dont have a
            # material, so just ignore them.
            if obj.Type != 'polymsh':
                continue
            geo = obj.ActivePrimitive.GetGeometry2(0)
            if obj.Material:
                materials.append(obj.Material)
            else:
                materials.append('Scene_Material')
            for cls in geo.Clusters:
                if cls.Material:
                    materials.append(cls.Material)
        return materials

    def material_name_dict(self):
        dict_ = {}
        lib = self.xsi.ActiveProject.ActiveScene.MaterialLibraries[0]
        for mat in lib.Items:
            dict_[mat.Name] = mat
        return dict_


class SIProgressBar(object):
    def __init__(self):
        self.bar = xsiui.ProgressBar

    def show(self):
        self.bar.Visible = True

    def hide(self):
        self.bar.Visible = False

    def set(self, maximum, capt, val=0, step=1):
        self.bar.Value = val
        if maximum:
            self.bar.Maximum = maximum
        else:
            self.bar.Maximum = 1
        self.bar.Caption = capt
        self.bar.Step = step

    def setc(self, capt):
        self.bar.Caption = capt

    def inc(self):
        self.bar.Increment()
