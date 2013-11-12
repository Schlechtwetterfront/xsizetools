#########################################################
#####                  mshjson                      #####
#####                                               #####
#####            Logic for msh to txt               #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
#########################################################
xsi = Application
import msh2
reload(msh2)
import msh2_unpack
reload(msh2_unpack)


def get_paths():
    params = PPG.Inspected(0).Parameters
    return params('mshpath').Value, params('txtpath').Value


def msh2txt_OnClicked():
    mshpath, txtpath = get_paths()
    if not mshpath or not txtpath:
        return
    unpacker = msh2_unpack.MSHUnpack(mshpath)
    msh = unpacker.unpack()
    msh.save_json(txtpath)


def txt2msh_OnClicked():
    mshpath, txtpath = get_paths()
    if not mshpath or not txtpath:
        return
    msh = msh2.Msh.load_json(txtpath)
    msh.save(mshpath)
