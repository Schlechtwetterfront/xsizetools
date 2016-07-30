'''
    Some misc functionality.
'''
import json
import softimage
import os
from datetime import datetime as dt
import logging


def get_current_version(versionpath):
    major = 0
    minor = 0
    build = 0000
    with open(versionpath, 'r') as fh:
        for index, line in enumerate(fh):
            major, minor, build = line.split('.')
            break
    return major, minor, build


class Timer():
    def __init__(self, text):
        self.text = text
        self.start_time = None
        self.result_time = None

    def __enter__(self):
        self.start_time = dt.now()

    def __exit__(self, type_, value, traceback):
        self.result_time = dt.now() - self.start_time
        logging.info(self.text, self.result_time.seconds, self.result_time.microseconds)


class CheckSel(object):
    def __init__(self, app, models, root, progbar):
        self.xsi = app
        self.models = models
        self.probs = []
        self.pb = progbar
        self.root = root

    def build_UI(self):
        for prop in self.root.Properties:
            if prop.Name == 'CSR':
                self.xsi.DeleteObj('CSR')
        ps = self.xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'CSR')
        lay = ps.PPGLayout
        lay.Language = "pythonscript"
        for p in self.probs:
            lay.AddTab(p['name'])
            lay.AddGroup('Warnings for {0}'.format(p['name']), 1)
            if p['type']:
                lay.AddStaticText('Bad model type: {0}'.format(p['type']))
            if p['sides']:
                lay.AddStaticText('Bad Faces')
                gp = ps.AddGridParameter('badpoly_{0}'.format(p['name']))
                bp = gp.Value
                bp.RowCount = len(p['sides'])
                bp.ColumnCount = 2
                bp.SetColumnLabel(0, 'Poly Index')
                bp.SetColumnLabel(1, 'Vertex Count')
                for index, el in enumerate(p['sides']):
                    bp.SetRowLabel(index, index)
                    bp.SetRowValues(index, el)
                grid = lay.AddItem(gp.Name)
                grid.SetAttribute('NoLabel', True)
                grid.SetAttribute('ColumnWidths', '25:80:100')
            if p['badcls']:
                lay.AddStaticText('Bad Clusters')
                gpc = ps.AddGridParameter('badcls_{0}'.format(p['name']))
                bc = gpc.Value
                bc.RowCount = len(p['badcls'])
                bc.ColumnCount = 2
                bc.SetColumnLabel(0, 'Cluster')
                bc.SetColumnLabel(1, 'Problem')
                for index, el in enumerate(p['badcls']):
                    bc.SetRowLabel(index, index)
                    bc.SetRowValues(index, el)
                gridc = lay.AddItem(gpc.Name)
                gridc.SetAttribute('NoLabel', True)
                gridc.SetAttribute('ColumnWidths', '25:80:250')
            if p['unncls']:
                lay.AddStaticText('Unnecessary Clusters')
                gpu = ps.AddGridParameter('unncls_{0}'.format(p['name']))
                bu = gpu.Value
                bu.RowCount = len(p['unncls'])
                bu.ColumnCount = 2
                bu.SetColumnLabel(0, 'Cluster')
                bu.SetColumnLabel(1, 'Problem')
                for index, el in enumerate(p['unncls']):
                    bu.SetRowLabel(index, index)
                    bu.SetRowValues(index, el)
                gridu = lay.AddItem(gpu.Name)
                gridu.SetAttribute('NoLabel', True)
                gridu.SetAttribute('ColumnWidths', '25:80:250')
            lay.EndGroup()
        self.xsi.InspectObj(ps, '', 'CheckSel Report', 4, False)
        for prop in self.root.Properties:
            if prop.Name == 'CSR':
                self.xsi.DeleteObj('CSR')

    def check(self):
        mdlnum = len(self.models)
        self.pb.set(mdlnum, 'Checking models({0}...'.format(mdlnum))
        self.pb.show()
        for index, model in enumerate(self.models):
            self.pb.setc('Checking {0}({1}/{2})...'.format(model.Name, index + 1, mdlnum))
            probs = {'type': '', 'sides': '', 'badcls': '', 'unncls': ''}
            if model.Type not in ('null', 'polymsh', 'bone', 'root', 'eff', 'Texture Support'):
                probs['type'] = model.Type
            if model.Type in ('null', 'bone', 'root', 'eff'):
                continue
            if model.Type == 'Texture Support':
                probs['type'] = '{0}(might cause problems, freeze to remove it)'.format(model.Type)
            if model.Type == 'polymsh':
                geo = model.ActivePrimitive.GetGeometry2(0)
                # Check sides per poly. More than 4 sides aren't supported.
                facets = geo.Facets
                bad_polies = []
                for facet in facets:
                    if facet.Points.Count > 4:
                        bad_polies.append((facet.Index, facet.Points.Count))
                probs['sides'] = bad_polies
                # Check clusters.
                bad = []
                unnecessary = []
                # Weight clusters.
                pnt = geo.Clusters.Filter('pnt')
                envs = 0
                for cls in pnt:
                    for prop in cls.Properties:
                        if prop.Type == 'envweights':
                            envs += 1
                        elif 'ZEC' in prop.Name:
                            continue
                        else:
                            unnecessary.append(('{0}|{1}'.format(cls.Name, prop.Name), 'Unnecessary(not weights)'))
                if envs > 1:
                    bad.append(('Weights', 'Only first weight property will be used.'))
                # Sample clusters.
                smp = geo.Clusters.Filter('sample')
                uvs = 0
                vcs = 0
                for cls in smp:
                    for prop in cls.Properties:
                        if prop.Type == 'uvspace':
                            uvs += 1
                        elif prop.Type == 'vertexcolor':
                            vcs += 1
                        else:
                            unnecessary.append((prop.Name, 'Unnecessary(not UVs/Vert Colors)'))
                if uvs > 1:
                    bad.append(('UVs', 'Only first UV property will be used.'))
                if vcs > 1:
                    bad.append(('Vertex Colors', 'Only first Vert Color property will be used.'))
                # Polygon clusters.
                poly = geo.Clusters.Filter('poly')
                for cls in poly:
                    if cls.Material.name == model.Material.Name:
                        unnecessary.append((cls.Name, 'Unnecessary(same material)'))
                probs['badcls'] = bad
                probs['unncls'] = unnecessary
            if probs['type'] or probs['sides'] or probs['badcls'] or probs['unncls']:
                probs['name'] = model.Name
                self.probs.append(probs)
        self.pb.hide()


class ExportStats(object):
    def __init__(self):
        self.models = 0
        self.mats = 0
        self.start = None
        self.end = None
        self.verts = 0
        self.faces = 0
        self.result = None

    def secs(self):
        if self.result:
            return self.result.seconds
        self.result = self.end - self.start
        return self.result.seconds

    def micros(self):
        if self.result:
            return self.result.microseconds
        self.result = self.end - self.start
        return self.result.seconds

def get_import_log_path():
    path = os.path.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'import_log.log')
    if os.path.exists(path):
        return path
    return None


def get_export_log_path():
    path = os.path.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'export_log.log')
    if os.path.exists(path):
        return path
    return None


def load_settings(settings_name='export', ppg=None):
    if ppg:
        return settings_from_ppg(settings_name, ppg)
    path = os.path.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'Resources', settings_name)
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except IOError:
        print 'Could not load settings from {0}.'.format(path)
        settings = get_default_settings(settings_name)
        save_settings(settings_name, settings)
        return settings


def save_settings(settings_name, settings):
    path = os.path.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'Resources', settings_name)
    print path
    with open(path, 'w') as f:
        f.write(json.dumps(settings, f))


def settings_from_ppg(settings_name, ppg):
    settings = get_default_settings(settings_name)
    params = ppg.Parameters
    for key in settings.keys():
        settings[key] = params(key).Value
    return settings


def get_default_settings(settings_name):
    if settings_name == 'export':
        sett = {
            'path': 'C:',
            'overwrite': False,
            'anim': False,
            'basepose': False,
            'rootname': False,
            'batch': False,
            'show_finished_dialog': True,
        }
        return sett
    elif settings_name == 'import':
        sett = {
            'path': 'C:',
            'texpath': 'C:',
            'btexpath': False,
            'framerange': True,
            'applyonly': False,
            'log': False,
            'triangulate': True,
            'nullsize': 0.2,
            'ignoregeo': False,
            'ignoreanim': False,
            'wirecol': False,
            'Rbone': 0.452,
            'Gbone': 0.918,
            'Bbone': 0.4,
            'Rroot': 0.2,
            'Groot': 0.3,
            'Broot': 0.8,
            'Reff': 0.5,
            'Geff': 0.23,
            'Beff': 0.1,
            'hideeffs': False,
            'hideroots': False,
            'weld': True,
            'show_finished_dialog': True,
        }
        return sett
