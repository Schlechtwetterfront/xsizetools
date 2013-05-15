#########################################################
#####                    misc                       #####
#####                                               #####
#####        Misc logic for various dialogs         #####
#####                                               #####
#####             code copyright (C)                #####
#####         Benedikt Schatz 2012-2013             #####
#####                                               #####
#####    https://sites.google.com/site/andescp/     #####
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


def openDocs_OnClicked():
    thepath = addonpath + "\\XSIZETools\\Resources\\Help\\Documentation.txt"
    webbrowser.open(thepath)


def launch_gt_OnClicked():
    url = "http://gametoast.com/forums/viewtopic.php?f=36&t=26664"
    webbrowser.open_new_tab(url)


def launch_website_OnClicked():
    url = "https://sites.google.com/site/andescp/zetools_main"
    webbrowser.open_new_tab(url)


def Close_OnClicked():
    PPG.Close()
    xsi.DeleteObj('ZETH')
