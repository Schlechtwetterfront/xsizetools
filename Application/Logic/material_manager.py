#########################################################
#####                XSIZETools                     #####
#####         code copyright (C) Ande 2012          #####
#####    https://sites.google.com/site/andescp/     #####
#####                                               #####
#####           Material Manager logic.             #####
#########################################################
from win32com.client import constants as const
import win32com.client
xsi = Application
addonpath = xsi.InstallationPath(const.siUserAddonPath)
PROJECTPATH = xsi.InstallationPath(const.siProjectPath)


def close_mat_OnClicked():
    PPG.Close()
    xsi.DeleteObj('MaterialEdit')


def help_mat_OnClicked():
    ps = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MatManagerHelp')
    lay = ps.PPGLayout
    lay.Language = 'pythonscript'
    agr = lay.AddGroup
    egr = lay.EndGroup
    text = lay.AddStaticText
    agr('Create', 1)
    text('''Create a phong material(the only supported material type)
with the specified name(line edit to the left of this button.''')
    egr()
    agr('Edit', 1)
    text('''Inspect the first selected material ZE flags and options can be
found here, too.''')
    egr()
    agr('ZEify / De-ZEify', 1)
    text('''Adds/Removes Zero Engine flags and material settings to the
selected material(s).''')
    egr()
    agr('Remove', 1)
    text('''Removes the selected material(s).''')
    egr()
    agr('Assign Tex', 1)
    text('''A shortcut to assign a texture to the diffuse slot of
the selected material. This will launch a file browser.''')
    egr()
    agr('Assign / Unassign', 1)
    text('''Assigns/unassigns the first selected material to the
currently selected models.''')
    egr()
    xsi.InspectObj(ps, '', 'MatManagerHelp', 4, False)
    for prop in xsi.ActiveSceneRoot.Properties:
        if prop.Name == 'MatManagerHelp':
            xsi.DeleteObj('MatManagerHelp')


def del_mat_OnClicked():
    materials = get_scene_materials()
    ppg = PPG.Inspected(0)
    sel = ppg.Parameters('materials').Value
    split = sel.split(';')
    lay = ppg.PPGLayout
    listbox = lay.Item('materials')
    items = listbox.UIItems
    print items
    print split
    items2 = list(items[:])
    print items2
    for matname in split:
        print matname
        for mat in materials:
            if mat.Name == matname:
                xsi.DeleteObj(mat)
                break
    refresh()
    PPG.Refresh()


def create_mat_OnClicked():
    ppg = PPG.Inspected(0)
    name = ppg.Parameters('mat_name').Value
    args = '$XSI_DSPRESETS\\Shaders\\Material\\Phong', name, '', '', False, ''
    xsi.SICreateMaterial(*args)
    refresh()


def edit_mat_OnClicked():
    materials = get_scene_materials()
    ppg = PPG.Inspected(0)
    sel = ppg.Parameters('materials').Value
    split = sel.split(';')
    for mat in materials:
        if mat.Name == split[0]:
            xsi.InspectObj(mat)


def add_flags_OnClicked():
    materials = get_scene_materials()
    ppg = PPG.Inspected(0)
    sel = ppg.Parameters('materials').Value
    split = sel.split(';')
    for matname in split:
        for mat in materials:
            if mat.Name == matname:
                if not get_msh_material_property(mat):
                    add_msh_material_flags(mat)
                    break
    refresh()


def del_flags_OnClicked():
    materials = get_scene_materials()
    ppg = PPG.Inspected(0)
    sel = ppg.Parameters('materials').Value
    split = sel.split(';')
    for matname in split:
        for mat in materials:
            if mat.Name == matname:
                prop = get_msh_material_property(mat)
                if prop:
                    xsi.DeleteObj(prop)
                break
    refresh()


def unassign_mat_OnClicked():
    if xsi.Selection.Count == 0:
        msg_box('No objects selected.')
        return
    xsi.SIUnAssignMaterial(xsi.Selection)


def assign_mat_OnClicked():
    materials = get_scene_materials()
    ppg = PPG.Inspected(0)
    sel = ppg.Parameters('materials').Value
    split = sel.split(';')
    mat2assign = None
    for mat in materials:
        if mat.Name == split[0]:
            mat2assign = mat
            break
    if xsi.Selection.Count == 0:
        msg_box('No objects selected.')
        return
    for item in xsi.Selection:
        if item.Type == 'polySubComponent':
            cls = item.SubComponent.CreateCluster('matpolycls')
            xsi.SIAssignMaterial(cls, mat2assign)
        elif item.Type == 'poly':
            xsi.SIAssignMaterial(item, mat2assign)
        elif item.Type == 'polymsh':
            xsi.SIAssignMaterial(item, mat2assign)
    refresh()


def assign_tex_OnClicked():
    materials = get_scene_materials()
    ppg = PPG.Inspected(0)
    sel = ppg.Parameters('materials').Value
    split = sel.split(';')
    mats = []
    for matname in split:
        for mat in materials:
            if mat.Name == matname:
                mats.append(mat)
                break
    xsiui = win32com.client.Dispatch('XSI.UIToolkit')
    fb = xsiui.FileBrowser
    fb.DialogTitle = 'Select a .tga file'
    fb.InitialDirectory = PROJECTPATH
    fb.Filter = 'TARGA (*.tga)|*.tga||'
    fb.ShowOpen()
    img_filepath = fb.FilePathName
    if img_filepath:
        for mat in mats:
            shader = xsi.CreateShaderFromPreset('$XSI_DSPRESETS\\Shaders\\Texture\\Image.Preset', mat)
            img_clip = xsi.SICreateImageClip2(img_filepath)
            xsi.SIConnectShaderToCnxPoint(img_clip, shader.tex, False)
            xsi.SIConnectShaderToCnxPoint(shader, mat.Shaders(0).Parameters('diffuse'), False)
##############################################################################
######################   HELPER FUNCTIONS   ##################################


def refresh():
    mats = get_scene_materials('variants')
    PPG.Inspected(0).PPGLayout.Item('materials').UIItems = mats
    PPG.Refresh()


def msg_box(message):
    XSIUIToolkit.MsgBox(message, 0, 'XSIZETools')
    return True


def get_msh_material_property(material):
    for prop in material.Properties:
        if 'ZeroEngine_Flags' in prop.Name:
            return prop


def add_msh_material_flags(mat):
    pset = mat.AddProperty('CustomProperty', False, 'ZeroEngine Flags')
    pset.AddParameter3('tex1', const.siString)
    pset.AddParameter3('tex2', const.siString)
    pset.AddParameter3('tex3', const.siString)

    pset.AddParameter3('emissive', const.siBool, 0, '', '', 0)
    pset.AddParameter3('glow', const.siBool, 0, '', '', 0)
    pset.AddParameter3('transparency', const.siInt4, 0, 0, 2, 0)
    pset.AddParameter3('hardedged', const.siBool, 0, '', '', 0)
    pset.AddParameter3('perpixel', const.siBool, 0, '', '', 0)
    pset.AddParameter3('additive', const.siBool, 0, '', '', 0)
    pset.AddParameter3('specular', const.siBool, 0, '', '', 0)
    pset.AddParameter3('rendertype', const.siInt4, 0, 0, 31, 0)
    pset.AddParameter3('data0', const.siInt4, 0, 0, 255, 0)
    pset.AddParameter3('data1', const.siInt4, 0, 0, 255, 0)

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


def get_scene_materials(listtype='list'):
    mats = []
    matlibs = xsi.ActiveProject.ActiveScene.MaterialLibraries
    for lib in matlibs:
        for mat in lib.Items:
            mats.append(mat)
    if listtype == 'variants':
        newmats = []
        for index, mat in enumerate(mats):
            name = [mat.Name]
            prop = get_msh_material_property(mat)
            usedby = mat.UsedBy
            if usedby.Count > 0:
                if prop:
                    name.append(' - ZE | {0}'.format(usedby.Count))
                else:
                    name.append(' - {0}'.format(usedby.Count))
            else:
                if prop:
                    name.append(' - ZE')
            newmats.append(''.join(name))
            newmats.append(mat.Name)
        return newmats
    return mats
