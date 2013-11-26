#########################################################
#####                  XSIZETools                   #####
#####                                               #####
#####       XSI Plugin defining commands and UI     #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################
import win32com.client
from win32com.client import constants as const
import sys
from datetime import datetime
tt = datetime.now

xsi = Application
uitk = XSIUIToolkit
utils = XSIUtils

ADDONPATH = xsi.InstallationPath(const.siUserAddonPath)


def add_to_path():
    orig_path = get_origin()
    corepath = utils.BuildPath(orig_path, 'Application', 'Core')
    if corepath not in sys.path:
        sys.path.append(corepath)
    modpath = utils.BuildPath(orig_path, 'Application', 'Modules')
    if modpath not in sys.path:
        sys.path.append(modpath)


def get_origin():
    orig_path = ''
    plugins = xsi.Plugins
    for p in plugins:
        #print p.Name
        if p.Name == 'XSIZETools':
            orig_path = p.OriginPath[:-20]
    return orig_path


def XSILoadPlugin(in_reg):
    in_reg.Author = 'Ande'
    in_reg.Name = 'XSIZETools'
    in_reg.Email = 'schlchtwtrfrnt@gmail.com'
    in_reg.URL = 'https://sites.google.com/site/andescp/'
    in_reg.Major = 1
    in_reg.Minor = 0

    in_reg.RegisterMenu(const.siMenuMainTopLevelID, 'ZE Tools', False)
    in_reg.RegisterCommand('XSIZETools', 'XSIZETools')
    in_reg.RegisterCommand('ZETHelp', 'ZETHelp')
    in_reg.RegisterCommand('MSHExport', 'MSHExport')
    in_reg.RegisterCommand('MSHImport', 'MSHImport')
    in_reg.RegisterCommand('MaterialEdit', 'MaterialEdit')
    in_reg.RegisterCommand('ClothCreate', 'ClothCreate')
    in_reg.RegisterCommand('EditCloth', 'EditCloth')
    in_reg.RegisterCommand('OpenImportLog', 'OpenImportLog')
    in_reg.RegisterCommand('MshJson', 'MshJson')

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
    sub_menu = win32com.client.Dispatch(oMenu.AddItem('.MSH Tools', const.siMenuItemSubmenu))
    sub_menu.AddCommandItem('Manage Materials...', 'MaterialEdit')
    sub_menu.AddCommandItem('Create Cloth...', 'ClothCreate')
    sub_menu.AddCommandItem('Edit Cloth...', 'EditCloth')
    sub_menu.AddCommandItem('MSH to TXT...', 'MshJson')
    sub_menu2 = win32com.client.Dispatch(oMenu.AddItem('General Tools', const.siMenuItemSubmenu))
    sub_menu2.AddCommandItem('Info...', 'ZETHelp')
    sub_menu2.AddCommandItem('Open Import Log', 'OpenImportLog')
    return True


def XSIZETools_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True

    return True


def XSIZETools_Execute():
    from andesicore import Softimage

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

    layout.SetAttribute(const.siUILogicFile, Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\zetools.py')
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

    bones = Softimage.get_objects('bone*')
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
    from andesicore import Softimage
    import andezetcore
    reload(andezetcore)
    #remove old custom property
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'ZETH':
            xsi.DeleteObj('ZETH')
    currver = andezetcore.get_current_version(Softimage.get_plugin_origin('XSIZETools') + '\\xsizet.ver')
    pset = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'ZETH')
    pset.AddParameter3('bitmap', const.siString)

    lay = pset.PPGLayout
    lay.SetAttribute(const.siUILogicFile, Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\misc.py')
    lay.Language = 'pythonscript'

    lay.AddGroup('XSIZETools', 1)
    imagepath = Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\zetools_a2pandemic.bmp'
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
    print 'sys.path', sys.path
    from andesicore import Softimage
    import andezetcore
    reload(andezetcore)
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MSHExport':
            xsi.DeleteObj('MSHExport')
    config = andezetcore.Config()
    config.from_file(Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\Config\\export.tcnt')

    pS = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MSHExport')
    pS.AddParameter3('mshpath', const.siString, config.retrieve('path'))
    pS.AddParameter3('expbit', const.siString, '')
    pS.AddParameter3('overwrite', const.siBool, bool(config.retrieve('overwrite')), '', '', 0, 0)
    pS.AddParameter3('anim', const.siBool, bool(config.retrieve('anim')), '', 0, 0, 0)  # last readonly
    pS.AddParameter3('basepose', const.siBool, bool(config.retrieve('basepose')), '', 0, 0)
    pS.AddParameter3('rootname', const.siBool, bool(config.retrieve('rootname')), '', 0, 0)
    pS.AddParameter3('batch', const.siBool, bool(config.retrieve('batch')), '', 0, 0)

    mLay = pS.PPGLayout
    mLay.SetAttribute(const.siUILogicFile, Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\exporter.py')
    mLay.Language = 'pythonscript'

    mLay.AddGroup('Export MSH', 1)  # G0
    mLay.AddRow()
    ctrlgrp = mLay.AddGroup('', False)
    ctrlgrp.SetAttribute(const.siUIWidthPercentage, 75)
    mLay.AddRow()  # 6
    mshPathI = mLay.AddItem('mshPath', 'MSH File', const.siControlFilePath)
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
    imagepath = Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\export_icon_zetools.bmp'
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
    from andesicore import Softimage
    print sys.path
    import andezetcore
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MSHImport':
            xsi.DeleteObj('MSHImport')
    config = andezetcore.ImportConfig()
    config.from_file(Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\Config\\import.tcnt')

    pS = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MSHImport')
    pS.AddParameter3('mshpath', const.siString, config.retrieve('path'))
    tp = pS.AddParameter3('texpath', const.siString, config.retrieve('texpath'))
    tp.SetCapabilityFlag(2, not bool(config.retrieve('btexpath')))
    pS.AddParameter3('btexpath', const.siBool, bool(config.retrieve('btexpath')), '', '', 0, 0)
    pS.AddParameter3('framerange', const.siBool, bool(config.retrieve('framerange')), '', '', 0, 0)
    pS.AddParameter3('applyonly', const.siBool, bool(config.retrieve('applyonly')), '', '', 0, 0)
    pS.AddParameter3('expbit', const.siString, '')
    pS.AddParameter3('ignoreanim', const.siBool, bool(config.retrieve('ignoreanim')), '', '', 0, 0)
    pS.AddParameter3('log', const.siBool, False, '', '', 0, 0)
    pS.AddParameter3('triangulate', const.siBool, True, '', '', 0, 0)
    pS.AddParameter3('ignoregeo', const.siBool, bool(config.retrieve('ignoregeo')), '', '', 0, 0)
    pS.AddParameter3('nullsize', const.siDouble, float(config.retrieve('nullsize')), 0.01, 5.0, 0, 0)
    pS.AddParameter3('wirecol', const.siBool, bool(config.retrieve('wirecol')), '', '', 0, 0)
    pS.AddParameter3('hideeffs', const.siBool, bool(config.retrieve('hideeffs')), '', '', 0, 0)
    pS.AddParameter3('hideroots', const.siBool, bool(config.retrieve('hideroots')), '', '', 0, 0)
    pS.AddParameter3('weld', const.siBool, bool(config.retrieve('weld')), '', '', 0, 0)

    col = config.retrieve('bonecol')
    r, g, b = [float(item) for item in col.split(' ')]
    pS.AddParameter3('Rbone', const.siDouble, r, 0.0, 1.0, 0, 0)
    pS.AddParameter3('Gbone', const.siDouble, g, 0.0, 1.0, 0, 0)
    pS.AddParameter3('Bbone', const.siDouble, b, 0.0, 1.0, 0, 0)

    col = config.retrieve('rootcol')
    r, g, b = [float(item) for item in col.split(' ')]
    pS.AddParameter3('Rroot', const.siDouble, r, 0.0, 1.0, 0, 0)
    pS.AddParameter3('Groot', const.siDouble, g, 0.0, 1.0, 0, 0)
    pS.AddParameter3('Broot', const.siDouble, b, 0.0, 1.0, 0, 0)

    col = config.retrieve('effcol')
    r, g, b = [float(item) for item in col.split(' ')]
    pS.AddParameter3('Reff', const.siDouble, r, 0.0, 1.0, 0, 0)
    pS.AddParameter3('Geff', const.siDouble, g, 0.0, 1.0, 0, 0)
    pS.AddParameter3('Beff', const.siDouble, b, 0.0, 1.0, 0, 0)

    mLay = pS.PPGLayout
    mLay.SetAttribute(const.siUILogicFile, Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\importer.py')
    mLay.Language = 'pythonscript'

    mLay.AddTab('Import')
    mLay.AddGroup('Import MSH', 1)  # G0
    mLay.AddRow()
    ctrlgrp = mLay.AddGroup('', False)
    ctrlgrp.SetAttribute(const.siUIWidthPercentage, 75)
    mLay.AddRow()  # 6
    mshPathI = mLay.AddItem('mshPath', 'MSH File', const.siControlFilePath)
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
    imagepath = Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\import_icon_zetools.bmp'
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
    from andesicore import Softimage
    import webbrowser
    import os.path as p
    path = p.join(Softimage.get_plugin_origin('XSIZETools'), 'import_log.log')
    if not p.isfile(path):
        uitk.MsgBox('Cant find {0}. Maybe you didnt import anything yet?'.format(path))
        return True
    webbrowser.open(path)
    return True


def MaterialEdit_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True

    return True


def MaterialEdit_Execute():
    from andesicore import Softimage
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MaterialEdit':
            xsi.DeleteObj('MaterialEdit')
    pset = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MaterialEdit')
    pset.AddParameter3('materials', const.siString)
    pset.AddParameter3('mat_name', const.siString, 'Phong')
    pset.AddParameter3('matbit', const.siString, '')
    mlay = pset.PPGLayout
    mlay.SetAttribute(const.siUILogicFile, Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\material_manager.py')
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
    listB.SetAttribute(const.siUICY, 175)
    listB.SetAttribute(const.siUICX, 150)
    listB.UIItems = materials
    mlay.EndGroup()
    ctrl = mlay.AddGroup('', 0)
    ctrl.SetAttribute(const.siUIWidthPercentage, 20)
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
    bit.SetAttribute(const.siUIWidthPercentage, 20)
    astbtn = mlay.AddButton('assign_tex', 'Assign Tex')
    astbtn.SetAttribute(const.siUICX, 65)
    assbtn = mlay.AddButton('assign_mat', 'Assign')
    assbtn.SetAttribute(const.siUICX, 65)
    unabtn = mlay.AddButton('unassign_mat', 'Unassign')
    unabtn.SetAttribute(const.siUICX, 65)
    imagepath = Softimage.get_plugin_origin('XSIZETools') + '\\Resources\\UI\\material_icon_zetools.bmp'
    expbitmap = mlay.AddEnumControl('matbit', None, '', const.siControlBitmap)
    expbitmap.SetAttribute(const.siUINoLabel, True)
    expbitmap.SetAttribute(const.siUIFilePath, imagepath)
    mlay.EndGroup()
    mlay.EndRow()
    mlay.EndGroup()

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'Material Manager')
    view.BeginEdit()
    view.Resize(320, 255)

    view.SetAttributeValue('targetcontent', pset.FullName)
    view.EndEdit()


def CLothCreate_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def ClothCreate_Execute():
    uitk.MsgBox('''Note: Cloth isnt fully implemented yet.
Cloth will be exported as cloth. However, it could crash
your game or not appear at all.''')
    if not xsi.Selection(0):
        uitk.MsgBox('No Model selected.')
        return
    prop = get_cloth_prop(xsi.Selection(0))
    if prop:
        uitk.MsgBox('Already is cloth.')
        return
    add_prop(xsi.Selection(0))
    edit_prop(xsi.Selection(0))


def EditCloth_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def EditCloth_Execute():
    if not xsi.Selection(0):
        uitk.MsgBox('No Model selected.')
        return
    edit_prop(xsi.Selection(0))


def MshJson_Init(in_ctxt):
    oCmd = in_ctxt.Source
    oCmd.Description = ''
    oCmd.ReturnValue = True
    return True


def MshJson_Execute():
    from andesicore import Softimage
    for x in xsi.ActiveSceneRoot.Properties:
        if x.Name == 'MshText':
            xsi.DeleteObj('MshText')

    pS = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'MshText')
    pS.AddParameter3('mshpath', const.siString, 'C:\\Users\\Administrator\\Documents\\')
    pS.AddParameter3('txtpath', const.siString, 'C:\\Users\\Administrator\\Documents\\')

    mLay = pS.PPGLayout
    mLay.SetAttribute(const.siUILogicFile, Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\mshjson.py')
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
    mLay.AddButton('msh2txt', 'MSH to TXT')
    mLay.AddButton('txt2msh', 'TXT to MSH')
    mLay.EndRow()

    mLay.EndGroup()

    desk = xsi.Desktop.ActiveLayout
    view = desk.CreateView('Property Panel', 'MSH Export')
    view.BeginEdit()
    view.Resize(400, 120)
    view.SetAttributeValue('targetcontent', pS.FullName)
    view.EndEdit()
    return True

#############################################################################################
#############################################################################################


def edit_prop(model):
    prop = get_cloth_prop(model)
    if prop:
        xsi.InspectObj(prop)
    else:
        uitk.MsgBox('Model is no cloth.')


def add_prop(model):
    from andesicore import Softimage
    ps = model.AddProperty('CustomProperty', False, 'ZECloth')
    ps.AddParameter3('collisions', const.siString)
    ps.AddParameter3('texture', const.siString)
    ps.AddParameter3('fixedcluster', const.siString)
    ps.AddParameter3('modelname', const.siString, model.Name)
    lay = ps.PPGLayout
    lay.SetAttribute(const.siUILogicFile, Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\cloth.py')
    lay.Language = 'pythonscript'
    arow = lay.AddRow
    erow = lay.EndRow
    agr = lay.AddGroup
    egr = lay.EndGroup
    item = lay.AddItem
    button = lay.AddButton

    agr('Fixed Points', 1)
    arow()
    button('pick_fixed', 'Pick Fixed Points')
    button('add_fixed', 'Add Fixed Points')
    button('remove_fixed', 'Clear Fixed Points')
    erow()
    egr()
    agr('Texture')
    item('texture', 'Texture')
    egr()
    agr('Collision')
    item('collisions', 'Collisions')
    arow()
    button('pick_coll', 'Pick Collisions')
    button('add_coll', 'Add Collisions')
    button('remove_colls', 'Clear Collisions')
    erow()
    egr()
    arow()
    button('del_prop', 'Remove Cloth')
    erow()


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
