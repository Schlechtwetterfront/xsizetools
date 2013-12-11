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
import os

TXTPATH = 'C:\\SWBF2_ModTools\\data_TST\\Worlds\\TST\\msh\\test\\abc.txt'
MSHPATH = 'C:\\SWBF2_ModTools\\data_TST\\Worlds\\TST\\msh\\nab2_prop_fountain.msh'
USE_HARD_PATHS = False


def get_paths():
    params = PPG.Inspected(0).Parameters
    if USE_HARD_PATHS or params('dev').Value:
        return MSHPATH, TXTPATH
    return params('mshpath').Value, params('txtpath').Value


def msh2txt_OnClicked():
    mshpath, txtpath = get_paths()
    if not mshpath or not txtpath:
        return
    unpacker = msh2_unpack.MSHUnpack(mshpath)
    msh = unpacker.unpack()
    if PPG.Inspected(0).Parameters('segmented').Value is True:
        msh.save_segmented_json(os.path.dirname(txtpath), os.path.basename(txtpath.split('.')[0]))
    else:
        msh.save_json(txtpath)


def txt2msh_OnClicked():
    mshpath, txtpath = get_paths()
    if not mshpath or not txtpath:
        return
    if PPG.Inspected(0).Parameters('segmented').Value is True:
        msh = msh2.Msh.load_segmented_json(os.path.dirname(txtpath), os.path.basename(txtpath.split('.')[0]))
    else:
        msh = msh2.Msh.load_json(txtpath)
    if PPG.Inspected(0).Parameters('dev').Value:
        msh.save(mshpath + '.msh')
    else:
        msh.save(mshpath)
