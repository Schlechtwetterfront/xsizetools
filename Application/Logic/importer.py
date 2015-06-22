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
import softimage
import andezetcore
import andezetimport
reload(softimage)
reload(andezetcore)
reload(andezetimport)
from win32com.client import constants as const
xsi = Application
ADDONPATH = xsi.InstallationPath(const.siUserAddonPath)
sigen = softimage.SIGeneral()


def store_flags_OnClicked():
    settings = andezetcore.load_settings('import', PPG.Inspected(0))
    andezetcore.save_settings('import', settings)
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
    agr('Weld Boundary Edges')
    text('''Applies a Weld Op to all geo models with a value of 0.01. The Operator
will persist after the import.''')
    egr()
    xsi.InspectObj(ps, '', 'ImportHelp', 4, False)
    for prop in xsi.ActiveSceneRoot.Properties:
        if prop.Name == 'ImportHelp':
            xsi.DeleteObj('ImportHelp')


def importbutton_OnClicked():
    settings = andezetcore.load_settings('import', PPG.Inspected(0))
    import_ = andezetimport.Import(xsi, settings)
    try:
        import_.import_()
    except SystemExit:
        return
    except Exception as e:
        if sigen.msg('Encountered an error while importing, copy error to clipboard?', const.siMsgYesNo) == 6:
            import win32clipboard, traceback
            log_path = andezetcore.get_import_log_path()
            lines = []
            if log_path:
                with open(log_path, 'r') as file_handle:
                    lines = file_handle.readlines()[-15:]
            message = ['Last 15 log lines:', '\n']
            message.extend(['\t{0}'.format(line.strip('\n')) for line in lines])
            message.extend(('\n', 'Traceback:', '\n'))
            message.extend(['\t{0}'.format(element) for element in traceback.format_exc().split('\n')])
            message = '\n'.join(message)

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(message, win32clipboard.CF_TEXT)
            win32clipboard.CloseClipboard()
        else:
            raise
    return


def EClose_OnClicked():
    PPG.Close()
    xsi.DeleteObj('MSHImport')
