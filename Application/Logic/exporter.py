#########################################################
#####                XSIZETools                     #####
#####         code copyright (C) Ande 2012          #####
#####    https://sites.google.com/site/andescp/     #####
#####                                               #####
#####             MSH Exporter logic.               #####
#########################################################
from win32com.client import constants as const
import win32com.client
import andesicore
import andezetcore
import andezetexport
reload(andezetcore)
reload(andesicore)
reload(andezetexport)
xsi = Application
addonpath = xsi.InstallationPath(const.siUserAddonPath)
sigen = andesicore.SIGeneral()


def store_flags_OnClicked():
    params = andezetcore.Config()
    params.from_ppg(PPG.Inspected(0))
    params.store(addonpath + '\\XSIZETools\\Resources\\Config\\export.tcnt')
    params.preview()
    sigen.msg('Stored.')
    return


def exportbutton_OnClicked():
    params = andezetcore.Config()
    params.from_ppg(PPG.Inspected(0))
    params.preview()
    export = andezetexport.Export(xsi, params)
    try:
        export.export()
    except SystemExit:
        return
    return


def check_sel_OnClicked():
    mdls = sigen.get_all_children(xsi.Selection(0))
    if not mdls:
        sigen.msg('No models selected.')
        return
    checksel = andezetcore.CheckSel(xsi, mdls, xsi.ActiveSceneRoot, andesicore.SIProgressBar())
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
