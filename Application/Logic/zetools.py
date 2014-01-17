#########################################################
#####                  zetools                      #####
#####                                               #####
#####            ZETools scripts logic              #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################
from win32com.client import constants as const
import softimage
reload(softimage)
xsi = Application
addonpath = xsi.InstallationPath(const.siUserAddonPath)


def makeaddon_OnClicked():
    oPPG = PPG.Inspected(0)
    addon_bone = oPPG.Parameters("addon_bone").Value
    print addon_bone, type(addon_bone)
    # Make sure the item is valid.
    # If no bones were found the item will be set to '1'.
    if addon_bone == '1':
        return
    addon_root_name = oPPG.Parameters("addon_root_name").Value
    xsi.GetPrim("Null", addon_root_name)
    xsi.MatchTransform(addon_root_name, addon_bone)


def setmesh_OnClicked():
    sel = xsi.Selection
    if sel.Count > 0:
        params = PPG.Inspected(0).Parameters
        root_name = params("addon_root_name").Value
        is_shadowvolume = params("addon_is_shadowvolume").Value
        if softimage.Softimage.get_object(root_name):
            if is_shadowvolume is True:
                xsi.CopyPaste(sel[0], '', root_name)
                selected_name = sel[0].Name
                sel[0].Name = "sv_" + selected_name
            elif is_shadowvolume is False:
                for item in sel:
                    xsi.CopyPaste(item, '', root_name)


def groupbones_OnClicked():
    bones = softimage.Softimage.get_objects('bone*')
    if bones:
        xsi.CreateGroup('Bones', bones)
