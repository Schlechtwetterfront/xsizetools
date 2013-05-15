#########################################################
#####                  importer                     #####
#####                                               #####
#####              MSH Importer logic               #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################
import andesicore
import andezetcore
import andezetimport
reload(andesicore)
reload(andezetcore)
reload(andezetimport)
from win32com.client import constants as const
xsi = Application
ADDONPATH = xsi.InstallationPath(const.siUserAddonPath)
sigen = andesicore.SIGeneral()


def store_flags_OnClicked():
    params = andezetcore.ImportConfig()
    params.from_ppg(PPG.Inspected(0))
    params.store(ADDONPATH + '\\XSIZETools\\Resources\\Config\\import.tcnt')
    sigen.msg('Stored.')
    return


def btexpath_OnChanged():
    ppg = PPG.Inspected(0)
    checked = ppg.Parameters('btexpath').Value
    texpath = ppg.Parameters('texpath')
    texpath.SetCapabilityFlag(2, not checked)


def help_OnClicked():
    ps = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'ImportHelp')
    lay = ps.PPGLayout
    lay.Language = "pythonscript"
    agr = lay.AddGroup
    egr = lay.EndGroup
    text = lay.AddStaticText
    agr('Import')
    text('Imports null-chain and animations from an animation .msh.')
    egr()
    agr('Texture Folder')
    text('''Sets the texture paths to that folder. If the box is unchecked the paths
will be set to the path of the .msh file.''')
    egr()
    agr('Set Frame Range')
    text('''Automatically sets the frame range from the animated frames in the
.msh file.''')
    egr()
    agr('Apply animation')
    text('''Only applies the unpacked animation to the selected hierarchy. Doesn't
import geometry/models or materials.''')
    egr()
    agr('Null Display Size')
    text('''Sets the display size of Nulls. Improves cleanness of the null
chain after import.''')
    egr()
    agr('Ignore Geometry')
    text('''Ignore geometry on import.''')
    egr()
    agr('Ignore Geometry')
    text('''Ignore animation on import.''')
    egr()
    agr('Color Nulls')
    text('''Colors nulls according to type(bone, root, eff).''')
    egr()
    agr('Hide Effs/Roots')
    text('''Hides nulls of the specified type on import.
Type is defined from certain strings appearing in the name:
bone_l_leg is a bone, even if it's no animated/weighted to.''')
    egr()
    agr('Debug')
    text('''Uses a different method to calculate CRCs (needed for animation).
This method is a lot slower than the usual one.''')
    egr()
    agr('"Safe" Import')
    text('''Uses a different method to calculate CRCs (needed for animation).
This method is slower than the usual one but not as slow as Debug.''')
    egr()
    agr('Weld Boundary Edges')
    text('''Applies a Weld Op to all geo models with a value of 0.01. The Operator
will persist after the import.''')
    egr()
    xsi.InspectObj(ps, '', 'ImportHelp', 4, False)
    for prop in xsi.ActiveSceneRoot.Properties:
        if prop.Name == 'ImportHelp':
            xsi.DeleteObj('ImportHelp')


def importbutton_OnClicked():
    params = andezetcore.ImportConfig()
    params.from_ppg(PPG.Inspected(0))
    import_ = andezetimport.Import(xsi, params)
    try:
        import_.import_()
    except SystemExit:
        return
    return


def EClose_OnClicked():
    PPG.Close()
    xsi.DeleteObj('MSHImport')
