'''
    Definition of commands, menus and UI.
'''
import win32com.client
from win32com.client import constants as const
import sys
import os
from datetime import datetime
tt = datetime.now

xsi = Application
uitk = XSIUIToolkit
utils = XSIUtils

ADDONPATH = xsi.InstallationPath(const.siUserAddonPath)

OLD_VERSION_MSG = '''You are using an old version of XSIZETools ({0}.{1}.{2}), please update to the latest ({3}.{4}.{5}).
Go to XSIZETools download page?'''

UP_TO_DATE_MSG = '''Build up to date (local: {0}.{1}.{2}, remote: {3}.{4}.{5}).'''

CHECK_VERSION_ERROR_MSG = 'Could not connect to github or timed out, version check not successful.'


def add_to_path():
    orig_path = get_origin()
    corepath = os.path.join(orig_path, 'Application', 'Core')
    if corepath not in sys.path:
        sys.path.append(corepath)
    modpath = os.path.join(orig_path, 'Application', 'Modules')
    if modpath not in sys.path:
        sys.path.append(modpath)


def get_origin():
    orig_path = ''
    plugins = xsi.Plugins
    for p in plugins:
        if p.Name == 'XSIZETools':
            orig_path = p.OriginPath[:-20]
    return orig_path


def check_version(quiet=False):
    add_to_path()
    import requests as req
    import webbrowser
    pb = uitk.ProgressBar
    pb.Caption = 'Checking XSIZETools Version...'
    pb.Visible = True
    pb.Maximum = 1

    origin = get_origin()
    verdir = os.path.abspath(os.path.join(origin, 'xsizet.ver'))
    with open(verdir, 'r') as fh:
        local_major, local_minor, local_build = fh.readline().split('.')
    try:
        latest = req.get('http://raw.github.com/Schlechtwetterfront/xsizetools/master/xsizet.ver')
    except (req.ConnectionError, req.Timeout):
        if quiet:
            pb.Visible = False
            return
        uitk.MsgBox(CHECK_VERSION_ERROR_MSG)
        pb.Visible = False
        return
    major, minor, build = latest.text.split('.')
    pb.Value = 1
    if int(build) > int(local_build):
        if uitk.MsgBox(OLD_VERSION_MSG.format(local_major, local_minor, local_build, major, minor, build), 4) == 6:
            webbrowser.open('http://schlechtwetterfront.github.io/xsizetools/')
    else:
        if quiet:
            pb.Visible = False
            return
        uitk.MsgBox(UP_TO_DATE_MSG.format(local_major, local_minor,
                                          local_build, major, minor, build))
    pb.Visible = False


def XSILoadPlugin(in_reg):
    in_reg.Author = 'Ande'
    in_reg.Name = 'XSIZETools'
    in_reg.Email = 'schlchtwtrfrnt@gmail.com'
    in_reg.URL = 'http://schlechtwetterfront.github.io/xsizetools/'
    in_reg.Major = 1
    in_reg.Minor = 0

    in_reg.RegisterMenu(const.siMenuMainTopLevelID, 'ZE Tools', False)
    in_reg.RegisterCommand('XSIZETools', 'XSIZETools')
    in_reg.RegisterCommand('ZETHelp', 'ZETHelp')
    in_reg.RegisterCommand('ZETOpenWebsite', 'ZETOpenWebsite')
    in_reg.RegisterCommand('MSHExport', 'MSHExport')
    in_reg.RegisterCommand('MSHImport', 'MSHImport')
    in_reg.RegisterCommand('MaterialEdit', 'MaterialEdit')
    in_reg.RegisterCommand('ClothCreate', 'ClothCreate')
    in_reg.RegisterCommand('EditCloth', 'EditCloth')
    in_reg.RegisterCommand('OpenImportLog', 'OpenImportLog')
    in_reg.RegisterCommand('OpenExportLog', 'OpenExportLog')
    in_reg.RegisterCommand('MshJson', 'MshJson')
    in_reg.RegisterCommand('ZETCheckVersion', 'ZETCheckVersion')

    in_reg.RegisterEvent('ZEToolsStartupEvent', const.siOnStartup)
    in_reg.RegisterTimerEvent('ZEToolsDelayedStartupEvent', 0, 1000)
    eventtimer = xsi.EventInfos('ZEToolsDelayedStartupEvent')
    eventtimer.Mute = True

    add_to_path()
    return True


def XSIUnloadPlugin(in_reg):
    return True


def ZEToolsStartupEvent_OnEvent(in_ctxt):
    evtimer = xsi.EventInfos('ZEToolsDelayedStartupEvent')
    evtimer.Mute = False
    return False


def ZEToolsDelayedStartupEvent_OnEvent(in_ctxt):
    from os.path import commonprefix
    for p in xsi.Plugins:
        if 'ZET' in p.Name:
            if len(commonprefix((p.OriginPath, ADDONPATH))) < 15:
                if uitk.MsgBox('''ZETools installed to the wrong directory.
Current dir: {0}
Should be: {1}
Try to move ZETools to the right dir?'''.format(p.OriginPath, ADDONPATH), 4) == 6:
                    import shutil
                    srcpath = p.OriginPath.split('\\')
                    srcpath = '\\'.join(srcpath[:-3])
                    dstpath = ADDONPATH + '\\XSIZETools'
                    shutil.copytree(srcpath, dstpath)
                    shutil.rmtree(srcpath)
                    uitk.MsgBox('''Moved dir to {0}.
    ZETools should work now but it's advised to restart XSI.'''.format(dstpath))
    return False


def ZETools_Init(in_ctxt):
    #define Menu
    oMenu = in_ctxt.Source
    oMenu.AddCommandItem('Scripts...', 'XSIZETools')
    oMenu.AddCommandItem('Export .MSH...', 'MSHExport')
    oMenu.AddCommandItem('Import .MSH...', 'MSHImport')
    oMenu.AddCommandItem('Cloth...', 'EditCloth')
    oMenu.AddCommandItem('Manage Materials...', 'MaterialEdit')
    sub_menu2 = win32com.client.Dispatch(oMenu.AddItem('Misc Tools', const.siMenuItemSubmenu))
    sub_menu2.AddCommandItem('MSH to TXT...', 'MshJson')
    sub_menu2.AddCommandItem('Info...', 'ZETHelp')
    sub_menu2.AddCommandItem('Help and Documentation', 'ZETOpenWebsite')
    sub_menu2.AddCommandItem('Open Import Log', 'OpenImportLog')
    sub_menu2.AddCommandItem('Open Export Log', 'OpenExportLog')
    sub_menu2.AddCommandItem('Check Version', 'ZETCheckVersion')
    return True


def ZETOpenWebsite_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True

    return True


def ZETOpenWebsite_Execute():
    import webbrowser
    url = 'http://schlechtwetterfront.github.io/xsizetools/'
    webbrowser.open_new_tab(url)
    return True


def ZETCheckVersion_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def ZETCheckVersion_Execute():
    check_version()
    return True


def XSIZETools_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True

    return True


def XSIZETools_Execute():
    add_to_path()
    import softimage
    reload(softimage)

    ppgname = 'ZEScripts'  # custom property name
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == ppgname:
            xsi.DeleteObj(ppgname)

    #create custom property
    property_set = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, ppgname)

    property_set.AddParameter3('addon_bone', const.siString, 1)
    property_set.AddParameter3('addon_root_name', const.siString, 'AddonRoot')
    property_set.AddParameter3('addon_is_shadowvolume', const.siBool, 0, '', '', 0)

    property_set.AddParameter2('Logo', const.siString, '', None, None, None, None, const.siClassifUnknown, const.siPersistable)
    layout = property_set.PPGLayout
    layout.Clear()

    layout.SetAttribute(const.siUILogicFile, softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\zetools.py')
    layout.Language = 'pythonscript'

    #layout.AddTab('Character Tools')

    layout.AddGroup('Bone Tools', 1)
    layout.AddButton('groupbones', 'Create Bone Group')
    layout.EndGroup()

    #layout.AddTab('Addon Tools')

    layout.AddGroup('Addon Mesh Setup', 1)
    layout.AddGroup('', 0)
    name_control = layout.AddItem('addon_root_name', 'Addon Root Name')
    name_control.SetAttribute('labelPercentage', 80)

    bones = softimage.Softimage.get_objects('bone*')
    # Create variants (display value/actual value).
    if len(bones) > 0:
        bone_variants = []
        for bone in bones:
            bone_variants.append(bone.Name)
            bone_variants.append(bone.FullName)
    else:
        bone_variants = ('No bones found.', 1)
    bone_control = layout.AddEnumControl('addon_bone', bone_variants, 'Addon Bone', const.siControlCombo)
    bone_control.SetAttribute('labelPercentage', 80)
    layout.EndGroup()
    layout.AddRow()
    layout.AddItem('addon_is_shadowvolume', 'Shadowvolume(sv_*)')
    layout.AddButton('makeaddon', 'Create Hierarchy')
    layout.AddButton('setmesh', 'Set As Addon Mesh')
    layout.EndRow()
    layout.EndGroup()

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'ZE Scripts')
    view.BeginEdit()
    view.Resize(400, 180)
    view.SetAttributeValue('targetcontent', property_set.FullName)
    view.EndEdit()
    return True


def ZETHelp_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True

    return True


def ZETHelp_Execute():
    add_to_path()
    import softimage
    reload(softimage)
    import andezetcore
    reload(andezetcore)
    #remove old custom property
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'ZETH':
            xsi.DeleteObj('ZETH')
    currver = andezetcore.get_current_version(softimage.Softimage.get_plugin_origin('XSIZETools') + '\\xsizet.ver')
    pset = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'ZETH')
    pset.AddParameter3('bitmap', const.siString)

    lay = pset.PPGLayout
    lay.SetAttribute(const.siUILogicFile, softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\misc.py')
    lay.Language = 'pythonscript'

    lay.AddGroup('XSIZETools', 1)
    imagepath = softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\zetools_a2pandemic.bmp'
    expbitmap = lay.AddEnumControl('bitmap', None, '', const.siControlBitmap)
    expbitmap.SetAttribute(const.siUINoLabel, True)
    expbitmap.SetAttribute(const.siUIFilePath, imagepath)
    lay.AddRow()
    lay.AddSpacer(90, 1)
    lay.AddStaticText('Version {0}'.format('.'.join([str(item) for item in currver])))
    lay.EndRow()
    lay.AddRow()
    lay.AddSpacer(60, 1)
    lay.AddStaticText('Code Copyright (C) Ande 2012')
    lay.EndRow()
    lay.AddRow()
    lay.AddStaticText('      http://schlechtwetterfront.github.io/xsizetools/', 290)
    lay.EndRow()
    lay.EndGroup()
    lay.AddGroup('Credits', 1)
    lay.AddStaticText('Credits for templates go to:' +
                      '\n\tAceMastermind' +
                      '\n\tDarthD.U.C.K.' +
                      '\n\tFragMe!' +
                      '\n\tpsych0fred' +
                      '\n\tAnde')
    lay.AddStaticText('Credits for .msh research go to:' +
                      '\n\tRileyman' +
                      '\n\tAnde' +
                      '\n\ttirpider' +
                      '\n\tAceMastermind' +
                      '\n\tFragMe!' +
                      '\n\tRepSharpshooter')
    lay.EndGroup()
    lay.AddGroup('Help', 1)
    lay.AddStaticText('For help, consult the XSIZETools homepage or' +
                      '\npost a topic on gametoast.com.', 280)
    lay.AddRow()
    lay.AddStaticText('Website:', 80)
    web = lay.AddButton('launch_website', 'Open Website in Browser')
    web.SetAttribute(const.siUICX, 140)
    lay.EndRow()
    lay.AddRow()
    lay.AddStaticText('Gametoast:', 80)
    gt = lay.AddButton('launch_gt', 'Open GT in Browser')
    gt.SetAttribute(const.siUICX, 140)
    lay.EndRow()
    lay.EndGroup()
    lay.AddRow()
    lay.AddStaticText('')
    lay.AddButton('Close', 'Close')
    lay.EndRow()

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'ZETools Info')
    view.BeginEdit()
    view.Resize(320, 540)
    view.SetAttributeValue('targetcontent', pset.FullName)
    view.EndEdit()

    return True


def MSHExport_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def MSHExport_Execute():
    add_to_path()
    import softimage
    reload(softimage)
    import andezetcore
    reload(andezetcore)
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MSHExport':
            xsi.DeleteObj('MSHExport')
    settings = andezetcore.load_settings('export')

    pS = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MSHExport')
    pS.AddParameter3('path', const.siString, settings.get('path'))
    pS.AddParameter3('expbit', const.siString, '')
    pS.AddParameter3('overwrite', const.siBool, settings.get('overwrite'), '', '', 0, 0)
    pS.AddParameter3('anim', const.siBool, settings.get('anim'), '', 0, 0, 0)  # last readonly
    pS.AddParameter3('basepose', const.siBool, settings.get('basepose'), '', 0, 0)
    pS.AddParameter3('rootname', const.siBool, settings.get('rootname'), '', 0, 0)
    pS.AddParameter3('batch', const.siBool, settings.get('batch'), '', 0, 0)

    mLay = pS.PPGLayout
    mLay.SetAttribute(const.siUILogicFile, softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\exporter.py')
    mLay.Language = 'pythonscript'

    mLay.AddGroup('Export MSH', 1)  # G0
    mLay.AddRow()
    ctrlgrp = mLay.AddGroup('', False)
    ctrlgrp.SetAttribute(const.siUIWidthPercentage, 75)
    mLay.AddRow()  # 6
    mshPathI = mLay.AddItem('path', 'MSH File', const.siControlFilePath)
    mshPathI.SetAttribute(const.siUINoLabel, 1)
    mshPathI.SetAttribute(const.siUIFileFilter, 'MSH File (*.msh)|*.msh')
    mshPathI.SetAttribute(const.siUIOpenFile, False)
    mshPathI.SetAttribute(const.siUIFileMustExist, False)
    mLay.EndRow()  # 6E

    mLay.AddRow()  # 4

    repgrp = mLay.AddGroup('Misc', 1)  # G2
    repgrp.SetAttribute(const.siUIWidthPercentage, 30)
    mLay.AddItem('overwrite', 'Auto-Overwrite')
    mLay.AddItem('rootname', 'Use root model name for .msh filename')
    mLay.AddItem('batch', 'Batch Export')
    mLay.EndGroup()  # G2E

    mLay.AddGroup('', 0)  # bbox and btns
    mLay.AddGroup('Animation')  # G1
    mLay.AddItem('anim', 'Export Animation')
    mLay.AddItem('basepose', 'Current frame as Basepose')
    mLay.EndGroup()  # G1E

    mLay.AddRow()  # 0
    mLay.AddGroup('', 0)  # G3
    mLay.AddRow()  # 1
    mLay.AddStaticText('')
    csbtn = mLay.AddButton('check_sel', 'Check Sel')
    csbtn.SetAttribute(const.siUICX, 80)
    helpbtn = mLay.AddButton('help', 'Help')
    helpbtn.SetAttribute(const.siUICX, 40)
    mLay.EndRow()  # 1E
    mLay.AddRow()  # 2
    mLay.AddStaticText('')
    storebtn = mLay.AddButton('store_flags', 'Store Flags')
    storebtn.SetAttribute(const.siUICX, 80)
    closebtn = mLay.AddButton('EClose', 'Close')
    closebtn.SetAttribute(const.siUICX, 40)
    mLay.EndRow()  # 2E
    mLay.EndGroup()  # G3E
    expgrp = mLay.AddGroup('', 0)  # G4
    expgrp.SetAttribute(const.siUIWidthPercentage, 1)
    mLay.AddRow()  # 3
    exportbtn = mLay.AddButton('exportbutton', 'Export')
    exportbtn.SetAttribute(const.siUICX, 75)
    exportbtn.SetAttribute(const.siUICY, 45)
    mLay.EndRow()  # 3E
    mLay.EndGroup()  # G4E
    mLay.EndRow()  # 0E
    mLay.EndGroup()  # bbox and btn

    mLay.EndRow()  # 4E
    mLay.EndGroup()  # Controls
    icongroup = mLay.AddGroup('', 0)
    icongroup.SetAttribute('WidthPercentage', 1)
    imagepath = softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\export_icon_zetools.bmp'
    expbitmap = mLay.AddEnumControl('expbit', None, '', const.siControlBitmap)
    expbitmap.SetAttribute(const.siUINoLabel, True)
    expbitmap.SetAttribute(const.siUIFilePath, imagepath)
    mLay.EndGroup()
    mLay.EndRow()
    mLay.EndGroup()  # G0E

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'MSH Export')
    view.BeginEdit()
    view.Resize(600, 190)
    view.SetAttributeValue('targetcontent', pS.FullName)
    view.EndEdit()
    return True


def MSHImport_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def MSHImport_Execute():
    add_to_path()
    import softimage
    reload(softimage)
    import andezetcore
    reload(andezetcore)
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MSHImport':
            xsi.DeleteObj('MSHImport')
    settings = andezetcore.load_settings('import')

    pS = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MSHImport')
    pS.AddParameter3('path', const.siString, settings.get('path'))
    tp = pS.AddParameter3('texpath', const.siString, settings.get('texpath'))
    tp.SetCapabilityFlag(2, not settings.get('btexpath'))
    pS.AddParameter3('btexpath', const.siBool, settings.get('btexpath'), '', '', 0, 0)
    pS.AddParameter3('framerange', const.siBool, settings.get('framerange'), '', '', 0, 0)
    pS.AddParameter3('applyonly', const.siBool, settings.get('applyonly'), '', '', 0, 0)
    pS.AddParameter3('expbit', const.siString, '')
    pS.AddParameter3('ignoreanim', const.siBool, settings.get('ignoreanim'), '', '', 0, 0)
    pS.AddParameter3('log', const.siBool, settings.get('log'), '', '', 0, 0)
    pS.AddParameter3('triangulate', const.siBool, settings.get('triangulate'), '', '', 0, 0)
    pS.AddParameter3('ignoregeo', const.siBool, settings.get('ignoregeo'), '', '', 0, 0)
    pS.AddParameter3('nullsize', const.siDouble, settings.get('nullsize'), 0.01, 5.0, 0, 0)
    pS.AddParameter3('wirecol', const.siBool, settings.get('wirecol'), '', '', 0, 0)
    pS.AddParameter3('hideeffs', const.siBool, settings.get('hideeffs'), '', '', 0, 0)
    pS.AddParameter3('hideroots', const.siBool, settings.get('hideroots'), '', '', 0, 0)
    pS.AddParameter3('weld', const.siBool, settings.get('weld'), '', '', 0, 0)

    pS.AddParameter3('Rbone', const.siDouble, settings.get('Rbone'), 0.0, 1.0, 0, 0)
    pS.AddParameter3('Gbone', const.siDouble, settings.get('Gbone'), 0.0, 1.0, 0, 0)
    pS.AddParameter3('Bbone', const.siDouble, settings.get('Bbone'), 0.0, 1.0, 0, 0)

    pS.AddParameter3('Rroot', const.siDouble, settings.get('Rroot'), 0.0, 1.0, 0, 0)
    pS.AddParameter3('Groot', const.siDouble, settings.get('Groot'), 0.0, 1.0, 0, 0)
    pS.AddParameter3('Broot', const.siDouble, settings.get('Broot'), 0.0, 1.0, 0, 0)

    pS.AddParameter3('Reff', const.siDouble, settings.get('Reff'), 0.0, 1.0, 0, 0)
    pS.AddParameter3('Geff', const.siDouble, settings.get('Geff'), 0.0, 1.0, 0, 0)
    pS.AddParameter3('Beff', const.siDouble, settings.get('Beff'), 0.0, 1.0, 0, 0)

    mLay = pS.PPGLayout
    mLay.SetAttribute(const.siUILogicFile, softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\importer.py')
    mLay.Language = 'pythonscript'

    mLay.AddTab('Import')
    mLay.AddGroup('Import MSH', 1)  # G0
    mLay.AddRow()
    ctrlgrp = mLay.AddGroup('', False)
    ctrlgrp.SetAttribute(const.siUIWidthPercentage, 75)
    mLay.AddRow()  # 6
    mshPathI = mLay.AddItem('path', 'MSH File', const.siControlFilePath)
    mshPathI.SetAttribute(const.siUINoLabel, 1)
    mshPathI.SetAttribute(const.siUIFileFilter, 'MSH File (*.msh)|*.msh')
    mshPathI.SetAttribute(const.siUIOpenFile, True)
    mshPathI.SetAttribute(const.siUIFileMustExist, True)
    mLay.EndRow()  # 6E

    mLay.AddRow()
    btp = mLay.AddItem('btexpath', 'Texture Folder')
    #btp.SetAttribute(const.siUINoLabel, 1)
    btp.SetAttribute(const.siUIWidthPercentage, 1)
    texPathI = mLay.AddItem('texpath', 'Texture Folder', const.siControlFolder)
    texPathI.SetAttribute(const.siUINoLabel, 1)
    texPathI.SetAttribute(const.siUIWidthPercentage, 55)
    mLay.EndRow()

    mLay.AddRow()  # 4

    repgrp = mLay.AddGroup('Misc', 1)  # G2
    repgrp.SetAttribute(const.siUIWidthPercentage, 35)
    mLay.AddItem('framerange', 'Set Frame Range')
    mLay.AddItem('applyonly', 'Apply animation to selected hierarchy')
    mLay.Additem('nullsize', 'Null Display Size')
    mLay.EndGroup()  # G2E

    bboxg = mLay.AddGroup('', 0)  # bbox and btns
    bboxg.SetAttribute(const.siUIWidthPercentage, 50)
    mLay.AddGroup('Ignore')  # G1
    mLay.Additem('ignoregeo', 'Ignore Geometry')
    mLay.Additem('ignoreanim', 'Ignore Animation')
    mLay.EndGroup()  # G1E

    mLay.AddRow()  # 0
    mLay.AddGroup('', 0)  # G3
    mLay.AddRow()  # 1
    mLay.AddStaticText('')
    helpbtn = mLay.AddButton('help', 'Help')
    helpbtn.SetAttribute(const.siUICX, 40)
    mLay.EndRow()  # 1E
    mLay.AddRow()  # 2
    mLay.AddStaticText('')
    storebtn = mLay.AddButton('store_flags', 'Store Flags')
    storebtn.SetAttribute(const.siUICX, 80)
    closebtn = mLay.AddButton('EClose', 'Close')
    closebtn.SetAttribute(const.siUICX, 40)
    mLay.EndRow()  # 2E
    mLay.EndGroup()  # G3E
    expgrp = mLay.AddGroup('', 0)  # G4
    expgrp.SetAttribute(const.siUIWidthPercentage, 1)
    mLay.AddRow()  # 3
    exportbtn = mLay.AddButton('importbutton', 'Import')
    exportbtn.SetAttribute(const.siUICX, 75)
    exportbtn.SetAttribute(const.siUICY, 45)
    mLay.EndRow()  # 3E
    mLay.EndGroup()  # G4E
    mLay.EndRow()  # 0E
    mLay.EndGroup()  # bbox and btn

    mLay.EndRow()  # 4E
    mLay.EndGroup()  # Controls
    icongroup = mLay.AddGroup('', 0)
    icongroup.SetAttribute('WidthPercentage', 1)
    imagepath = softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\import_icon_zetools.bmp'
    expbitmap = mLay.AddEnumControl('expbit', None, '', const.siControlBitmap)
    expbitmap.SetAttribute(const.siUINoLabel, True)
    expbitmap.SetAttribute(const.siUIFilePath, imagepath)
    mLay.EndGroup()
    mLay.EndRow()
    mLay.EndGroup()  # G0E

    mLay.AddTab('Settings')
    mLay.AddGroup('Settings')
    mLay.AddRow()
    mLay.AddGroup('Colors')
    mLay.AddItem('wirecol', 'Color Nulls')
    mLay.AddRow()
    mLay.AddColor('Rbone', 'Bones', False)
    mLay.AddSpacer(1, 0)
    mLay.AddColor('Rroot', 'Roots', False)
    mLay.AddSpacer(1, 0)
    mLay.AddColor('Reff', 'Effs', False)
    mLay.EndRow()
    mLay.EndGroup()

    mLay.AddGroup('', 0)
    mLay.AddGroup('Misc')
    mLay.AddItem('hideroots', 'Hide Roots')
    mLay.AddItem('hideeffs', 'Hide Effectors')
    mLay.AddItem('weld', 'Weld Boundary Edges')
    mLay.AddItem('log', 'Log MSH Unpack')
    mLay.AddItem('triangulate', 'Triangulate')
    mLay.EndGroup()
    mLay.AddRow()
    mLay.AddStaticText('')
    mLay.AddButton('EClose', 'Close')
    mLay.EndRow()
    mLay.EndGroup()
    mLay.EndRow()
    mLay.EndGroup()

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'MSH Import')
    view.BeginEdit()
    view.Resize(600, 240)
    view.SetAttributeValue('targetcontent', pS.FullName)
    view.EndEdit()
    return True


def OpenImportLog_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def OpenImportLog_Execute():
    add_to_path()
    import softimage
    reload(softimage)
    import webbrowser
    import os.path as p
    path = p.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'import_log.log')
    if not p.isfile(path):
        uitk.MsgBox('Cant find {0}. Maybe you didnt import anything yet?'.format(path))
        return True
    webbrowser.open(path)
    return True


def OpenExportLog_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def OpenExportLog_Execute():
    add_to_path()
    import softimage
    reload(softimage)
    import webbrowser
    import os.path as p
    path = p.join(softimage.Softimage.get_plugin_origin('XSIZETools'), 'export_log.log')
    if not p.isfile(path):
        uitk.MsgBox('Cant find {0}. Maybe you didnt export anything yet?'.format(path))
        return True
    webbrowser.open(path)
    return True


def MaterialEdit_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True

    return True


def MaterialEdit_Execute():
    add_to_path()
    import softimage
    reload(softimage)
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MaterialEdit':
            xsi.DeleteObj('MaterialEdit')
    pset = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MaterialEdit')
    pset.AddParameter3('materials', const.siString)
    pset.AddParameter3('mat_name', const.siString, 'Phong')
    pset.AddParameter3('matbit', const.siString, '')
    mlay = pset.PPGLayout
    mlay.SetAttribute(const.siUILogicFile, softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\material_manager.py')
    mlay.Language = 'pythonscript'

    materials = get_scene_materials('variants')

    mlay.AddGroup('Material Manager', 1)
    mlay.AddRow()
    box = mlay.AddGroup('', 0)
    box.SetAttribute(const.siUIWidthPercentage, 50)
    matname = mlay.AddItem('mat_name', '')
    matname.SetAttribute(const.siUINoLabel, True)
    listB = mlay.AddEnumControl('Materials', '', 'Materials', const.siControlListBox)
    listB.SetAttribute('NoLabel', True)
    listB.SetAttribute('MultiSelectionListBox', True)
    listB.SetAttribute(const.siUICY, 350)
    # listB.SetAttribute(const.siUICX, 150)
    listB.UIItems = materials
    mlay.EndGroup()
    buttons_group = mlay.addGroup('', 0)
    buttons_group.SetAttribute(const.siUIWidthPercentage, 20)
    mlay.AddRow()
    ctrl = mlay.AddGroup('', 0)
    # ctrl.SetAttribute(const.siUIWidthPercentage, 20)
    crebtn = mlay.AddButton('create_mat', 'Create')
    crebtn.SetAttribute(const.siUICX, 55)
    edibtn = mlay.AddButton('edit_mat', 'Edit')
    edibtn.SetAttribute(const.siUICX, 55)
    addbtn = mlay.AddButton('add_flags', 'ZEify')
    addbtn.SetAttribute(const.siUICX, 55)
    defbtn = mlay.AddButton('del_flags', 'De-ZEify')
    defbtn.SetAttribute(const.siUICX, 55)
    delbtn = mlay.AddButton('del_mat', 'Remove')
    delbtn.SetAttribute(const.siUICX, 55)
    mlay.AddSpacer(1, 45)
    helbtn = mlay.AddButton('help_mat', 'Help')
    helbtn.SetAttribute(const.siUICX, 55)
    clobtn = mlay.AddButton('close_mat', 'Close')
    clobtn.SetAttribute(const.siUICX, 55)
    mlay.EndGroup()
    bit = mlay.AddGroup('', 0)
    # bit.SetAttribute(const.siUIWidthPercentage, 20)
    astbtn = mlay.AddButton('assign_tex', 'Assign Tex')
    astbtn.SetAttribute(const.siUICX, 65)
    assbtn = mlay.AddButton('assign_mat', 'Assign')
    assbtn.SetAttribute(const.siUICX, 65)
    unabtn = mlay.AddButton('unassign_mat', 'Unassign')
    unabtn.SetAttribute(const.siUICX, 65)
    imagepath = softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\material_icon_zetools.bmp'
    expbitmap = mlay.AddEnumControl('matbit', None, '', const.siControlBitmap)
    expbitmap.SetAttribute(const.siUINoLabel, True)
    expbitmap.SetAttribute(const.siUIFilePath, imagepath)
    mlay.EndGroup()
    mlay.EndRow()
    mlay.EndGroup()
    mlay.EndRow()
    mlay.EndGroup()

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'Material Manager')
    view.BeginEdit()
    view.Resize(400, 450)

    view.SetAttributeValue('targetcontent', pset.FullName)
    view.EndEdit()


def CLothCreate_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def ClothCreate_Execute():
    add_to_path()
    if not xsi.Selection(0):
        uitk.MsgBox('No Model selected.')
        return
    prop = get_cloth_prop(xsi.Selection(0))
    if prop:
        if uitk.MsgBox('Already is cloth, delete the existing cloth and create a new one?', 4) == 6:
            xsi.DeleteObj(prop)
        else:
            return
    import utils
    utils.add_cloth_property(xsi.Selection(0))
    edit_prop(xsi.Selection(0))


def EditCloth_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def EditCloth_Execute():
    add_to_path()
    if not xsi.Selection(0):
        uitk.MsgBox('No Model selected.')
        return
    prop = get_cloth_prop(xsi.Selection(0))
    if prop:
        edit_prop(xsi.Selection(0))
    else:
        import utils
        utils.add_cloth_property(xsi.Selection(0))
        edit_prop(xsi.Selection(0))


def MshJson_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def MshJson_Execute():
    add_to_path()
    import softimage
    reload(softimage)
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MshText':
            xsi.DeleteObj('MshText')

    pS = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MshText')
    pS.AddParameter3('mshpath', const.siString, 'C:\\Users\\Administrator\\Documents\\')
    pS.AddParameter3('txtpath', const.siString, 'C:\\Users\\Administrator\\Documents\\')
    pS.AddParameter3('segmented', const.siBool, True, 0, 1, 0, 0)
    pS.AddParameter3('dev', const.siBool, False, 0, 1, 0, 0)

    mLay = pS.PPGLayout
    mLay.SetAttribute(const.siUILogicFile, softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\mshjson.py')
    mLay.Language = 'pythonscript'

    mLay.AddGroup('MSH Text', 1)

    mshPathI = mLay.AddItem('mshpath', 'MSH File', const.siControlFilePath)
    mshPathI.SetAttribute(const.siUINoLabel, 0)
    mshPathI.SetAttribute(const.siUIFileFilter, 'MSH File (*.msh)|*.msh')
    mshPathI.SetAttribute(const.siUIOpenFile, False)
    mshPathI.SetAttribute(const.siUIFileMustExist, False)

    txtPathI = mLay.AddItem('txtpath', 'TXT File', const.siControlFilePath)
    txtPathI.SetAttribute(const.siUINoLabel, 0)
    txtPathI.SetAttribute(const.siUIFileFilter, 'TXT File (*.txt)|*.txt')
    txtPathI.SetAttribute(const.siUIOpenFile, False)
    txtPathI.SetAttribute(const.siUIFileMustExist, False)

    mLay.AddRow()
    mLay.AddItem('segmented', 'Segmented')
    mLay.AddItem('dev', 'DevMode')
    mLay.AddButton('msh2txt', 'MSH to TXT')
    mLay.AddButton('txt2msh', 'TXT to MSH')
    mLay.EndRow()

    mLay.EndGroup()

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'MSH to TXT')
    view.BeginEdit()
    view.Resize(400, 125)
    view.SetAttributeValue('targetcontent', pS.FullName)
    view.EndEdit()
    return True

#############################################################################################
#############################################################################################


def edit_prop(model):
    prop = get_cloth_prop(model)
    if prop:
        xsi.InspectObj(prop, '', 'Edit Cloth', const.siLockAndForceNew)
    else:
        uitk.MsgBox('Model is no cloth.')


def get_cloth_prop(model):
    try:
        if model:
            for prop in model.Properties:
                if 'ZECloth' in prop.Name:
                    return prop
    except:
        return False


def check_existence_bool(obj_name):
    xsifact = win32com.client.Dispatch('XSI.Factory')
    collection = xsifact.CreateObject('XSI.Collection')
    collection.items = obj_name
    if collection.Count == 1:
        return True
    return False


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


def get_msh_material_property(material):
    for prop in material.Properties:
        if 'ZeroEngine_Flags' in prop.Name:
            return prop
