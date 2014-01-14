#########################################################
#####                    misc                       #####
#####                                               #####
#####        Misc logic for various dialogs         #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    http://schlechtwetterfront.github.io/      #####
#########################################################
from win32com.client import constants as const
import webbrowser
xsi = Application


def close_csr_OnClicked():
    PPG.Close()
    xsi.DeleteObj('CSR')


def ERClose_OnClicked():
    PPG.Close()
    xsi.DeleteObj('ExportReport')


def launch_gt_OnClicked():
    url = 'http://gametoast.com/forums/viewtopic.php?f=36&t=26664'
    webbrowser.open_new_tab(url)


def launch_website_OnClicked():
    url = 'http://schlechtwetterfront.github.io/xsizetools/'
    webbrowser.open_new_tab(url)


def Close_OnClicked():
    PPG.Close()
    xsi.DeleteObj('ZETH')
