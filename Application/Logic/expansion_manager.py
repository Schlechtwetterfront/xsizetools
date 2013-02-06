#########################################################
#####                XSIZETools                     #####
#####         code copyright (C) Ande 2012          #####
#####    https://sites.google.com/site/andescp/     #####
#####                                               #####
#####              Expansion Logic.                 #####
#########################################################
import win32com.client
from win32com.client import constants as const
import os #modules for different stuff
import webbrowser
import shutil

addonpath = Application.InstallationPath(const.siUserAddonPath)

def addExp_OnClicked():#add expansion function
    log("Adding expansion")
    xsi = Application#saves time
    
    xsiuitoolkit = win32com.client.Dispatch( 'XSI.UIToolkit' )#some sort of hack
    
    oFB = xsiuitoolkit.FileBrowser #create file browser object
    oFB.DialogTitle = "Select an Expansion"
    oFB.InitialDirectory = addonpath
    oFB.Filter = "Text Containers (*.tcnt)|*.tcnt||"
    oFB.ShowOpen()
    
    #vars for storage
    newTemplates = []
    oldTemplates = []
    
    epCount = 0
    writtenEps = 0
    
    #use filebrowser results
    if oFB.FilePathName != "":
        log("Reading new expansion file")
        expfile = open(oFB.FilePathName,"r")#read new expansion file
        for line in expfile:
            if line[:1] == "#" or line[:1] == "[":
                pass
            elif line[:2] == "ep":
                newTemplates.append(line)
            elif line[:1] == "c" or "v" or "w":
                newTemplates.append(line)
                if line[:2] == "c " or "v " or "w " and line[-1:] == "\n":
                    if line[-1:] == "\n":
                        shutil.copy(oFB.FilePath + line[2:-1] + ".xsi", addonpath + "\\XSIZETools\\Resources\\Templates\\")
                    else:
                        shutil.copy(oFB.FilePath + line[2:] + ".xsi", addonpath + "\\XSIZETools\\Resources\\Templates\\")
            elif line == "":
                pass
        expfile.close()
        log("New expansion file read")    
        log("Reading main templates file")
        templRead = open(addonpath + "\\XSIZETools\\Resources\\Templates\\templates.tcnt","r")#read old expansion file
        for line in templRead:
            xsi.LogMessage(line[:2])
            if line[:1] == "c" or line[:1] == "v" or line[:1] == "w":
                oldTemplates.append(line)
                log("found template")
            elif line[:2] == "ep":
                oldTemplates.append(line)
                log("found ep")
                epCount += 1
            elif line == "":
                pass
            elif line[:1] == "#":
                pass
        templRead.close()
        log("Main templates file read")

        log("writing temp templates file")
        templWrite = open(addonpath + "\\XSIZETools\\Resources\\Templates\\templates_tmp.tcnt","w")#write temp template file(safer)from data collected from new expansion and old templates.tcnt file
        for element in oldTemplates:
            if element[:2] == "ep":
                if writtenEps == 0: #expansions get numbered from 0 to x
                    templWrite.write("[0]\n")
                    writtenEps += 1
                    templWrite.write(element)
                    log("wrote old template + num")
                elif writtenEps > 0 and writtenEps <= epCount:
                    templWrite.write("[end]\n")
                    templWrite.write("[" + str(writtenEps) + "]\n")
                    templWrite.write(element)
                    writtenEps += 1
                    log("wrote old template + end + num")
            elif element[0] == "c" or element[0] == "v" or element[0] == "w":
                templWrite.write(element)
            #templWrite.close()
            log("elements from main templates file written")
            for element in newTemplates:
                if element[:2] == "ep":
                    if writtenEps == 0:
                        templWrite.write("[0]\n")
                        writtenEps += 1
                        templWrite.write(element)
                        log("wrote new template + 0")
                    elif writtenEps > 0 and writtenEps <= epCount:
                        templWrite.write("[end]\n")
                        templWrite.write("[" + str(writtenEps) + "]\n")
                        templWrite.write(element)
                        writtenEps += 1
                        log("wrote new template + num and end")
                elif element[0] == "c" or element[0] == "v" or element[0] == "w":
                    if element[-1:] == "\n":
                        templWrite.write(element)
                    else:
                        templWrite.write(element + "\n")
            templWrite.write("[end]")
        templWrite.close()
        log("elements from new expansion file written")
        os.remove(addonpath + "\\XSIZETools\\Resources\\Templates\\templates.tcnt") #if everything worked allright, remove old template file and
        os.rename(addonpath + "\\XSIZETools\\Resources\\Templates\\templates_tmp.tcnt", addonpath + "\\XSIZETools\\Resources\\Templates\\templates.tcnt")#rename temp template file to templates.tcnt
        log("renamed and removed temp and old main template file")

    else:
        xsi.LogMessage("cancelled")
    
    PPG.Close() #close PPG and
    xsi.manageExpansions()#rebuild it in order to update listbox content(AFAIK not the best way, but EASY)


def remExp_OnClicked():#remove selected expansion
    log("removing expansion")
    xsi = Application
    oPPG = PPG.Inspected(0)
    selEp = int(oPPG.Parameters("instExp").Value)#get selection value
    selEp -= 1
    xsi.LogMessage("[" + str(selEp) + "]")
    
    toDel = []
    toMem = []
    epCount = 0
    writtenEps = 0
    
    if selEp == 0:
        log( "cancelled" )
    else:
        tF = open(addonpath + "\\XSIZETools\\Resources\\Templates\\templates.tcnt","r")#read template file
        ignore = False
        log("reading main template file")
        #store everything between [selection value+1] and [end] in toDel list, else in toMem list
        for line in tF:
            if line[:3] == "[" + str(selEp) + "]":
                ignore = True
                log("Now ignoring")
            elif line[:5] == "[end]":
                ignore = False
                log("Stopped ignoring")
            elif line[0] == "c" or line[0] == "v" or line[0] == "w": #######TEMPLATES
                if ignore == True:
                    toDel.append(line)
                    log("Ignored Template")
                elif ignore == False:
                    toMem.append(line)
                    log("Appended template")
            elif line[:2] == "ep": #######EP
                if ignore == True:
                    log("Ignored Ep")
                elif ignore == False:
                    toMem.append(line)
                    epCount += 1
                    log("Appended Ep and counted")
            elif line[0] == "#":
                pass
            else:
                log("Else")
        tF.close()
                    
        log("read main template file")
        log("writing temp templates file")
        tFt = open(addonpath + "\\XSIZETools\\Resources\\Templates\\templates_tmp.tcnt","w")#write temp template file from toMem list
        for element in toMem:
            if element[:2] == "ep":
                if writtenEps == 0:
                    tFt.write("[0]\n")
                    writtenEps += 1
                    tFt.write(element)
                    log("wrote old template + num")
                elif writtenEps > 0 and writtenEps <= epCount:
                    tFt.write("[end]\n")
                    tFt.write("[" + str(writtenEps) + "]\n")
                    tFt.write(element)
                    writtenEps += 1
                    log("wrote old template + end + num")
            elif element[0] == "c" or element[0] == "v" or element[0] == "w":
                tFt.write(element)
        tFt.write("[end]")    
        tFt.close()
        log("finished writing temp template file")
        
        os.remove(addonpath + "\\XSIZETools\\Resources\\Templates\\templates.tcnt")#remove old file and replace with temp file
        os.rename(addonpath + "\\XSIZETools\\Resources\\Templates\\templates_tmp.tcnt", addonpath + "\\XSIZETools\\Resources\\Templates\\templates.tcnt")
        log("renamed and removed temp and old templates file")
        
        log("removing template files")
        a = 0
        for element in toDel:#remove files from toDel list
            if element[0] == "c" or element[0] == "v" or element[0] == "w":
                thepath2 = element[2:-1] + ".xsi"
                a += 1
                os.remove(addonpath + "\\XSIZETools\\Resources\\Templates\\" + thepath2)#this produced an unicode decode error for a long time, dunno why, seems to work now
        log("removed " + str(a) + " .xsis")
    PPG.Close()#close PPG
    Application.manageExpansions()#and rebuild to refresh
    

def EClose_OnClicked():
    PPG.Close()
    Application.DeleteObj('ExpansionManager')


def log( text ):
    Application.LogMessage( text )
