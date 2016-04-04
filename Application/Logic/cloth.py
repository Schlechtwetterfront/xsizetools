'''
    UI functionality for the cloth dialog.
'''
xsi = Application
from win32com.client import constants as const
import win32com.client
import softimage
sigen = softimage.SIGeneral()
ADDONPATH = xsi.InstallationPath(const.siUserAddonPath)


def del_prop_OnClicked():
    ppg = PPG.Inspected(0)
    remove_fixed(PPG.Inspected(0))
    xsi.DeleteObj(ppg)
    PPG.Close()


def pick_fixed_OnClicked():
    ppg = PPG.Inspected(0)
    xsi.SelectObj(ppg.Parent)
    xsi.SetPointSelectionFilter()
    picked = xsi.PickElement('point', 'Pick Points', 'Pick Points')
    remove_fixed(PPG.Inspected(0))
    xsi.CreateClusterFromSubComponent(picked[2], 'ZEFixedPoints')


def remove_fixed_OnClicked():
    remove_fixed(PPG.Inspected(0))


def add_fixed_OnClicked():
    xsi.SetPointSelectionFilter()
    picked = xsi.PickElement('point', 'Pick Points', 'Pick Points')
    fixed = get_fixed_cluster(PPG.Inspected(0).Parent)
    if fixed:
        xsi.SIAddToCluster(fixed, picked[2])
        return
    xsi.CreateClusterFromSubComponent(picked[2], 'ZEFixedPoints')


def pick_coll_OnClicked():
    picked = xsi.PickElement('object', 'Pick Collision Object(s)', 'Pick Collision Object(s)')
    ppg = PPG.Inspected(0)
    ppg.Parameters('collisions').Value = ','.join(element.FullName for element in picked[2])


def remove_coll_OnClicked():
    ppg = PPG.Inspected(0)
    ppg.Parameters('collisions').Value = ''


def add_coll_OnClicked():
    ppg = PPG.Inspected(0)
    ppg.Parameters('collisions').Value = ','.join(element.FullName for element in xsi.Selection)


def select_coll_OnClicked():
    ppg = PPG.Inspected(0)
    if ppg.Parameters('collisions').Value:
        collisions = ppg.Parameters('collisions').Value.split(',')
        xsi.SelectObj(collisions)

####################################################################


def remove_fixed(ppg):
    if not ppg.Parent.ActivePrimitive.GetGeometry2(0):
        return

    fixed = get_fixed_cluster(ppg.Parent)
    if fixed:
        xsi.DeleteObj(fixed)


def find_model(objName):
    xsifact = win32com.client.Dispatch("XSI.Factory")
    oColl = xsifact.CreateObject("XSI.Collection")
    oColl.items = objName
    if oColl.Count > 0:
        return oColl(0)
    else:
        return False


def get_fixed_cluster(model):
    geo = model.ActivePrimitive.GetGeometry2(0)
    for cls in geo.Clusters:
        if 'ZEFixed' in cls.Name:
            return cls


def get_cloth_prop(model):
    try:
        if model:
            for prop in model.Properties:
                if 'ZECLoth' in prop.Name:
                    return prop
    except:
        return False
