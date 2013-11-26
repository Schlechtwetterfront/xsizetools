#########################################################
#####                 andezetcore                   #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################
from xml.etree.ElementTree import ElementTree, Element, SubElement, dump


def get_current_version(versionpath):
    major = 0
    minor = 0
    export = 0
    import_ = 0
    with open(versionpath, 'r') as fh:
        for index, line in enumerate(fh):
            if index == 0:
                major = int(line.strip())
            elif index == 1:
                minor = int(line.strip())
            elif index == 2:
                export = int(line.strip())
            elif index == 3:
                import_ = int(line.strip())
    return major, minor, export, import_


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


class Config(object):
    def __init__(self):
        self.tree = None
        self.path = None

    def from_file(self, path):
        self.path = path
        try:
            self.tree = ElementTree(file=path)
        except (SyntaxError, IOError):
            self.default()

    def from_ppg(self, ppg):
        config = Element('config')
        path = SubElement(config, 'path')
        path.text = ppg.Parameters('mshpath').Value
        overwrite = SubElement(config, 'overwrite')
        overwrite.text = int(ppg.Parameters('overwrite').Value) * 'True'
        anim = SubElement(config, 'anim')
        anim.text = int(ppg.Parameters('anim').Value) * 'True'
        basepose = SubElement(config, 'basepose')
        basepose.text = int(ppg.Parameters('basepose').Value) * 'True'
        rootname = SubElement(config, 'rootname')
        rootname.text = int(ppg.Parameters('rootname').Value) * 'True'
        batch = SubElement(config, 'batch')
        batch.text = int(ppg.Parameters('batch').Value) * 'True'
        self.tree = ElementTree(element=config)

    def default(self):
        config = Element('config')
        path = SubElement(config, 'path')
        path.text = 'C:'
        overwrite = SubElement(config, 'overwrite')
        overwrite.text = ''
        anim = SubElement(config, 'anim')
        anim.text = ''
        basepose = SubElement(config, 'basepose')
        basepose.text = ''
        rootname = SubElement(config, 'rootname')
        rootname.text = ''
        batch = SubElement(config, 'batch')
        batch.text = ''

        self.tree = ElementTree(element=config)

    def retrieve(self, tagname):
        tag = self.tree.find(tagname)
        try:
            return tag.text
        except Exception:
            self.default()
            return self.retrieve(tagname)

    def preview(self):
        dump(self.tree.getroot())

    def set(self, tagname, text):
        tag = self.tree.find(tagname)
        tag.text = text

    def store(self, path=None):
        if path:
            self.tree.write(path)
            return
        self.tree.write(self.path)
        return


class ImportConfig(Config):
    def from_ppg(self, ppg):
        config = Element('config')
        path = SubElement(config, 'path')
        path.text = ppg.Parameters('mshpath').Value
        print 'ImportConfig path: {0}'.format(path.text)
        texpath = SubElement(config, 'texpath')
        texpath.text = ppg.Parameters('texpath').Value
        btexpath = SubElement(config, 'btexpath')
        btexpath.text = int(ppg.Parameters('btexpath').Value) * 'True'
        framerange = SubElement(config, 'framerange')
        framerange.text = int(ppg.Parameters('framerange').Value) * 'True'
        applyonly = SubElement(config, 'applyonly')
        applyonly.text = int(ppg.Parameters('applyonly').Value) * 'True'
        log = SubElement(config, 'log')
        log.text = int(ppg.Parameters('log').Value) * 'True'
        triangulate = SubElement(config, 'triangulate')
        triangulate.text = int(ppg.Parameters('triangulate').Value) * 'True'
        nullsize = SubElement(config, 'nullsize')
        nullsize.text = str(ppg.Parameters('nullsize').Value)
        ignoregeo = SubElement(config, 'ignoregeo')
        ignoregeo.text = int(ppg.Parameters('ignoregeo').Value) * 'True'
        ignoreanim = SubElement(config, 'ignoreanim')
        ignoreanim.text = int(ppg.Parameters('ignoreanim').Value) * 'True'
        wirecol = SubElement(config, 'wirecol')
        wirecol.text = int(ppg.Parameters('wirecol').Value) * 'True'
        bonecol = SubElement(config, 'bonecol')
        bonecol.text = '{0} {1} {2}'.format(ppg.Parameters('Rbone').Value,
                                            ppg.Parameters('Gbone').Value,
                                            ppg.Parameters('Bbone').Value)
        rootcol = SubElement(config, 'rootcol')
        rootcol.text = '{0} {1} {2}'.format(ppg.Parameters('Rroot').Value,
                                            ppg.Parameters('Groot').Value,
                                            ppg.Parameters('Broot').Value)
        effcol = SubElement(config, 'effcol')
        effcol.text = '{0} {1} {2}'.format(ppg.Parameters('Reff').Value,
                                           ppg.Parameters('Geff').Value,
                                           ppg.Parameters('Beff').Value)
        hideeffs = SubElement(config, 'hideeffs')
        hideeffs.text = int(ppg.Parameters('hideeffs').Value) * 'True'
        hideroots = SubElement(config, 'hideroots')
        hideroots.text = int(ppg.Parameters('hideroots').Value) * 'True'
        weld = SubElement(config, 'weld')
        weld.text = int(ppg.Parameters('weld').Value) * 'True'
        self.tree = ElementTree(element=config)

    def default(self):
        print 'default called'
        config = Element('config')
        path = SubElement(config, 'path')
        path.text = 'C:'
        texpath = SubElement(config, 'texpath')
        texpath.text = 'C:'
        btexpath = SubElement(config, 'btexpath')
        btexpath.text = ''
        framerange = SubElement(config, 'framerange')
        framerange.text = ''
        applyonly = SubElement(config, 'applyonly')
        applyonly.text = ''
        log = SubElement(config, 'log')
        log.text = ''
        debug = SubElement(config, 'debug')
        debug.text = ''
        safe = SubElement(config, 'safe')
        safe.text = ''
        triangulate = SubElement(config, 'triangulate')
        triangulate.text = ''
        ignoregeo = SubElement(config, 'ignoregeo')
        ignoregeo.text = ''
        ignoreanim = SubElement(config, 'ignoreanim')
        ignoreanim.text = ''
        nullsize = SubElement(config, 'nullsize')
        nullsize.text = '0.2'
        wirecol = SubElement(config, 'wirecol')
        wirecol.text = ''
        bonecol = SubElement(config, 'bonecol')
        bonecol.text = '0.452 0.918 0.4'
        rootcol = SubElement(config, 'rootcol')
        rootcol.text = '0.2 0.3 0.8'
        effcol = SubElement(config, 'effcol')
        effcol.text = '0.5 0.23 0.1'
        hideeffs = SubElement(config, 'hideeffs')
        hideeffs.text = ''
        hideroots = SubElement(config, 'hideroots')
        hideroots.text = ''
        weld = SubElement(config, 'weld')
        weld.text = ''
        self.tree = ElementTree(element=config)
