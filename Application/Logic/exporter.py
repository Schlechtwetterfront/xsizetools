'''
    UI functionality for the export dialog.
'''
from win32com.client import constants as const
import win32com.client
import softimage
import andezetcore
import andezetexport
reload(andezetcore)
reload(softimage)
reload(andezetexport)
xsi = Application
addonpath = xsi.InstallationPath(const.siUserAddonPath)
sigen = softimage.SIGeneral()


def store_flags_OnClicked():
    settings = andezetcore.load_settings('export', PPG.Inspected(0))
    andezetcore.save_settings('export', settings)
    sigen.msg('Stored.')
    return


def exportbutton_OnClicked():
    settings = andezetcore.load_settings('export', PPG.Inspected(0))
    export = andezetexport.Export(xsi, settings)
    try:
        export.export()
    except SystemExit:
        return
    except Exception as e:
        if sigen.msg('Encountered an error while exporting, copy error to clipboard?', const.siMsgYesNo) == 6:
            import win32clipboard, traceback
            log_path = andezetcore.get_export_log_path()
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


def check_sel_OnClicked():
    mdls = sigen.get_all_children(xsi.Selection(0))
    if not mdls:
        sigen.msg('No models selected.')
        return
    checksel = andezetcore.CheckSel(xsi, mdls, xsi.ActiveSceneRoot, softimage.SIProgressBar())
    checksel.check()
    checksel.build_UI()


def help_OnClicked():
    ps = xsi.ActiveSceneRoot.AddProperty('CustomProperty', False, 'Export Help')
    lay = ps.PPGLayout
    lay.Language = "pythonscript"
    agr = lay.AddGroup
    egr = lay.EndGroup
    text = lay.AddStaticText
    agr('Auto-Overwrite', 1)
    text('Overwrites output files if they already exist.')
    egr()
    agr('Root model name for .msh filename')
    text('''Usees the name of the hierarchy root as filename.
Has to be enabled when using Batch Export.''')
    egr()
    agr('Batch Export', 1)
    text('''Loops through all direct children of the current
selection and exports each one with all its children. Root
model name for .msh filename has to be enabled for this.''')
    egr()
    agr('Animation')
    text('''Exports animation from the current frame range.
Current frame as Basepose only exports the selected frame
and the following to minimize file size. Export Animation
has to be enabled.''')
    egr()
    agr('Buttons')
    text('''Check Sel iterates through the current hierarchy and analyses
every model for problems which could break the export and smaller
problems like unnecessary clusters.
Store Flags stores the current config(path, checked boxes etc).
Export should be self-explanatory.''')
    egr()
    xsi.InspectObj(ps, '', 'Export Help', 4, False)
    for prop in xsi.ActiveSceneRoot.Properties:
        if prop.Name == 'Export_Help':
            xsi.DeleteObj('Export_Help')


def basepose_OnChanged():
    ppg = PPG.Inspected(0)
    if ppg.Parameters('basepose').Value:
        ppg.Parameters('anim').Value = True


def anim_OnChanged():
    ppg = PPG.Inspected(0)
    if not ppg.Parameters('anim').Value:
        ppg.Parameters('basepose').Value = False


def batch_OnChanged():
    ppg = PPG.Inspected(0)
    if ppg.Parameters('batch').Value:
        ppg.Parameters('rootname').Value = True


def EClose_OnClicked():
    PPG.Close()
    xsi.DeleteObj('MSHExport')
