'''
    Misc utilities.
'''

def add_cloth_property(model):
    import softimage
    reload(softimage)
    import win32com
    from win32com.client import constants as const
    ps = model.AddProperty('CustomProperty', False, 'ZECloth')
    ps.AddParameter3('collisions', const.siString)
    ps.AddParameter3('texture', const.siString)
    ps.AddParameter3('fixedcluster', const.siString)
    ps.AddParameter3('modelname', const.siString, model.Name)
    lay = ps.PPGLayout
    lay.SetAttribute(const.siUILogicFile, softimage.Softimage.get_plugin_origin('XSIZETools') + '\\Application\\Logic\\cloth.py')
    lay.Language = 'pythonscript'
    arow = lay.AddRow
    erow = lay.EndRow
    agr = lay.AddGroup
    egr = lay.EndGroup
    item = lay.AddItem
    button = lay.AddButton

    agr('Texture')
    item('texture', 'Texture')
    egr()
    agr('Collision')
    item('collisions', 'Collisions')
    arow()
    # button('pick_coll', 'Pick Collisions')
    button('add_coll', 'Add from Selection')
    button('select_coll', 'Add to Selection')
    button('remove_coll', 'Clear')
    erow()
    egr()
    arow()
    fixed_points_group = agr('Fixed Points', 1)
    fixed_points_group.SetAttribute(const.siUIWidthPercentage, 20)
    arow()
    button('pick_fixed', 'Pick')
    # button('add_fixed', 'Add Fixed Points')
    button('remove_fixed', 'Clear')
    erow()
    egr()
    remove_button = button('del_prop', 'Remove Cloth')
    remove_button.SetAttribute(const.siUICY, 40)
    remove_button.SetAttribute(const.siUIWidthPercentage, 80)
    erow()

    return ps
