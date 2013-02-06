#########################################################
#####               msh2_framework                  #####
#####                 CRC tool                      #####
#####         code copyright (C) Ande 2012          #####
#####    https://sites.google.com/site/andescp/     #####
#####                                               #####
#####   drcrc.exe copyright (C) PandemicStudios(?)  #####
#########################################################
import subprocess
import _subprocess
import win32clipboard as w
import os

MODULEPATH = os.path.dirname(__file__)


class CRCError(Exception):
    def __init__(self, val):
        self.val = val

    def __str__(self):
        return '{0}'.format(self.val)


def crc(string):
    '''Returns the Zero CRC of 'string' as a string. Fastest.'''
    # Setup startup info to try and suppress the flashing drcrc.exe window.
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = _subprocess.SW_HIDE
    w.OpenClipboard(0)
    w.EmptyClipboard()
    w.SetClipboardText(string)
    w.CloseClipboard()
    exepath = os.path.join(MODULEPATH, 'drcrc.exe')
    subprocess.call(exepath, startupinfo=startupinfo)
    w.OpenClipboard()
    crc_ = w.GetClipboardData()
    w.EmptyClipboard()
    w.CloseClipboard()
    # Trim it so I only have the actual CRC left.
    crc_ = crc_[7:15]
    # Now reverse the order in pairs.
    crc_2 = (crc_[6:8], crc_[4:6], crc_[2:4], crc_[0:2])
    return hextranslate(''.join(crc_2))


def crc_safe(string):
    '''Returns the Zero CRC of 'string' as a string. Less prone to fail.'''
    # Setup startup info to try and suppress the flashing drcrc.exe window.
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = _subprocess.SW_HIDE
    w.OpenClipboard(0)
    w.EmptyClipboard()
    w.SetClipboardText(string)
    w.CloseClipboard()
    exepath = os.path.join(MODULEPATH, 'drcrc.exe')
    subprocess.call(exepath, startupinfo=startupinfo, shell=True)
    w.OpenClipboard()
    crc_ = w.GetClipboardData()
    w.EmptyClipboard()
    w.CloseClipboard()
    # Trim it so I only have the actual CRC left.
    crc_ = crc_[7:15]
    # Now reverse the order in pairs.
    crc_2 = (crc_[6:8], crc_[4:6], crc_[2:4], crc_[0:2])
    return hextranslate(''.join(crc_2))


def crc_debug(string):
    '''Returns the Zero CRC of 'string' as a string. Debug version.'''
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= _subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = _subprocess.SW_HIDE
    w.OpenClipboard(0)
    w.EmptyClipboard()
    w.SetClipboardText(string)
    w.CloseClipboard()
    exepath = os.path.join(MODULEPATH, 'drcrc.exe')
    try:
        subprocess.call(exepath, startupinfo=startupinfo, shell=True)
    except WindowsError, ioe:
        raise CRCError('subprocess.call: shell=True({0}'.format(ioe))
    w.OpenClipboard()
    crc_ = w.GetClipboardData()
    w.EmptyClipboard()
    w.CloseClipboard()
    # Trim it so I only have the actual CRC left.
    crc_ = crc_[7:15]
    # Now reverse the order in pairs.
    crc_2 = (crc_[6:8], crc_[4:6], crc_[2:4], crc_[0:2])
    try:
        return hextranslate(''.join(crc_2))
    except ValueError, e:
        raise CRCError('hextranslate of "{0}" ({1})'.format(''.join(crc_2), e))


def compare_crc_adv(possible_strings, crc_):
    for string in possible_strings:
        if crc_ == crc(string):
            return string


def hextranslate(s):
    res = ""
    for i in range(len(s) / 2):
        realIdx = i * 2
        res = res + chr(int(s[realIdx:realIdx + 2], 16))
    return res
