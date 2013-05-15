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
import win32com.client
from win32com.client import constants as const
xsi = Application
addonpath = Application.InstallationPath(const.siUserAddonPath)



def CharTemplImp_OnClicked():#######IMPORT FUNCTIONS
    oPPG = PPG.Inspected(0)
    charIt = oPPG.Parameters("CharTempl").Value #get drop down menu selection value
    log("CharImport initiated.")
    templateImport("c",int(charIt)) #call import command
    
def WeapTemplImp_OnClicked():
    oPPG = PPG.Inspected(0)
    weapIt = oPPG.Parameters("WeapTempl").Value
    log("WeapImport initiated.")
    templateImport("w",int(weapIt))
    
def VehTemplImp_OnClicked():
    oPPG = PPG.Inspected(0)
    vehIt = oPPG.Parameters("VehTempl").Value
    log("VehImport initiated.")
    templateImport("v",int(vehIt))
###################################################

#############ADDON FUNCTIONS
def makeAddon_OnClicked():
    log("Creating Addon.")
    bones = getBoneList()
    if bones == False:
        log("No Bones existing!")
    else:
        oPPG = PPG.Inspected(0)
        addonBone = oPPG.Parameters("addonBone").Value
        addonRName = oPPG.Parameters("addonRName").Value
        xsi.GetPrim("Null", addonRName)
        xsi.MatchTransform(addonRName, bones[int(addonBone)-1])
        log("Created Addon.")
    
def setAddonMesh_OnClicked():
    log("Setting Addon Mesh")
    Sel = checkSel()
    if Sel.Count == 0:
        log("No Selection.")
    else:
        oPPG = PPG.Inspected(0)
        aR = oPPG.Parameters("addonRName").Value
        aSV = oPPG.Parameters("addonSV").Value
        if checkExistence(aR) == True:
            a = 0
            if aSV == True:
                xsi.CopyPaste(Sel[0],"",aR)
                nm = Sel[0].Name
                Sel[0].Name = "sv_" + nm
                log("SV Addon Mesh Set for " + addonRName )
            elif aSV == False:
                for el in Sel:
                    xsi.CopyPaste(el,"",aR)
                    a += 1
                log(str(a) + " Addon Meshes Set for " + addonRName )
        else:
            log("""Addon Root'""" + aR +"""' doesnt exist""")
        
######################################################

#################VEHICLE FUNCTIONS
def printOpt_OnClicked():
    oPPG = PPG.Inspected(0)
    turretName = oPPG.Parameters("turrName").Value
    
    XSIUIToolkit.Msgbox("Put this into your .msh.option file: " +
    "  -keep " + turretName + "_aimer_y" + " " + turretName + "_aimer_x" +
    "              This only outputs the content for the current turret, remember to reference all your turrets in the .msh.option")
    
def makeTurrX_OnClicked():
    log("Setting aimer x model")
    oPPG = PPG.Inspected(0)
    turretName = oPPG.Parameters("turrName").Value
    
    Sel = checkSel()
    if Sel.Count == 0:
        log("No Selection.")
    else:
        a = 0
        for el in Sel:
            a += 1
            xsi.CopyPaste( el , "" , turretName + "_aimer_x")
        log(str(a) + turretName + "_aimer_x model(s) set")
    
def makeTurrY_OnClicked():
    log("Setting aimer y model")
    oPPG = PPG.Inspected(0)
    turretName = oPPG.Parameters("turrName").Value
    
    Sel = checkSel()
    if Sel.Count == 0:
        log("No Selection.")
    else:
        a = 0
        for el in Sel:
            a += 1
            xsi.CopyPaste( el , "" , turretName + "_aimer_y")
        log(str(a) + turretName + "_aimer_y model(s) set")
    
def makeTurrBase_OnClicked():
    log("Setting turret base model")
    oPPG = PPG.Inspected(0)
    turretName = oPPG.Parameters("turrName").Value
    
    Sel = checkSel()
    if Sel.Count == 0:
        log("No Selection.")
    else:
        a = 0
        for el in Sel:
            a += 1
            xsi.CopyPaste( el , "" , turretName + "_root")
        log(str(a) + turretName + " base model(s) set")
    
def turrHier_OnClicked():
    log("Creating turret hierarchy")
    oPPG = PPG.Inspected(0)
    fire = oPPG.Parameters("fireNodeNumTurr").Value
    turretName = oPPG.Parameters("turrName").Value
    
    xsi.GetPrim("Null",turretName + "_root")
    xsi.GetPrim("Null",turretName + "_aimer_y",turretName + "_root")
    xsi.GetPrim("Null",turretName + "_aimer_x",turretName + "_aimer_y")
    if fire > 0:
        for n in range(1,fire+1):
            xsi.GetPrim("Null","hp_fire"+str(n),turretName + "_aimer_x")
            xsi.SetValue("hp_fire"+str(n)+".null.primary_icon",10)
    log("Created turret " + str(turretName) + "with " + str(fire) + "hp_fire's")
            
def vehHier_OnClicked():
    log("Creating vehicle hierarchy")
    oPPG = PPG.Inspected(0)
    fire = oPPG.Parameters("fireNodeNum").Value
    driver = oPPG.Parameters("driverNodeNum").Value
    exhaust = oPPG.Parameters("exhaustNodeNum").Value
    
    xsi.GetPrim("Null","DummyRoot")
    if fire > 0:
        for n in range(1,fire+1):
            xsi.GetPrim("Null","hp_fire"+str(n),"DummyRoot")
            xsi.SetValue("hp_fire"+str(n)+".null.primary_icon",10)
            xsi.Translate("hp_fire"+str(n),0.0,0.0,1.0)
    
    if driver > 0:
        for n in range(1,driver+1):
            xsi.GetPrim("Null","hp_driver"+str(n),"DummyRoot")
            xsi.SetValue("hp_driver"+str(n)+".null.primary_icon",6)
    
    if exhaust > 0:
        for n in range(1,driver+1):
            xsi.GetPrim("Null","hp_exhaust"+str(n),"DummyRoot")
            xsi.SetValue("hp_exhaust"+str(n)+".null.primary_icon",5)
            xsi.Translate("hp_exhaust"+str(n),0.0,0.0,-1.0)
    log("Created vehicle hierarchy with " + str(fire) + " hp_fires, " + str(driver) + " hp_drivers, " + str(exhaust) + " hp_exhausts")
            
def setVMdl_OnClicked():
    log("Setting vehicle model")
    oPPG = PPG.Inspected(0)
    vsv = oPPG.Parameters("vehSV").Value
    
    Sel = checkSel()
    if Sel.Count == 0:
        log("No Selection.")
    else:
        if vsv == True:
            xsi.CopyPaste(Sel[0],"","DummyRoot")
            nm = Sel[0].Name
            Sel[0].Name = "sv_" + nm
            log("vehicle sv set")
        elif vsv == False:
            a = 0
            for el in Sel:
                a += 1
                xsi.CopyPaste(el,"","DummyRoot")
            log(str(a) + " Vehicle model(s) set.")
    
#####################################################################################
#
###################WEAPON FUNCTIONS
def weapHier_OnClicked():
    log(" Creating weapon hierarchy.")
    xsi.GetPrim("Null","DummyRoot")
    xsi.GetPrim("Null","hp_fire","DummyRoot")
    xsi.SetValue("hp_fire.null.primary_icon",10)
    xsi.Translate("hp_fire",0.0,0.0,1)
    log("Created weap hierarchy")
    
def setWMdl_OnClicked():
    log("Setting weapon model")
    oPPG = PPG.Inspected(0)
    wsv = oPPG.Parameters("weapSV").Value
    
    Sel = checkSel()
    if Sel.Count == 0:
        log("No Selection.")
    else:
        if wsv == True:
            xsi.CopyPaste(Sel[0],"","DummyRoot")
            nm = Sel[0].Name
            Sel[0].Name = "sv_" + nm
            log("Weapon sv set")
        elif wsv == False:
            a = 0
            for el in Sel:
                a += 1
                xsi.CopyPaste(el,"","DummyRoot")
            log(str(a) + " Weapon model(s) set.")
    
#####################################################################################

###################CHARACTER FUNCTIONS
def SetMdl_OnClicked():
    log("Setting character model.")
    Sel = checkSel()
    oPPG = PPG.Inspected(0)
    ovrCnt = oPPG.Parameters("overrideCount").Value
    delEx = oPPG.Parameters("delExst").Value
    mdlK = oPPG.Parameters("mdlKind").Value
    if Sel.Count == 0:
        log("No Selection.")
    else:
        if mdlK == "1":
            if ovrCnt == 1:
                xsi.CopyPaste(Sel[0],"","DummyRoot")
                Sel[0].Name = "override_texture"
                log("override_texture set")
            elif ovrCnt == 2:
                xsi.CopyPaste(Sel[0],"","DummyRoot")
                Sel[0].Name = "override_texture2"
                log("override_texture2 set")
        elif mdlK == "2":
            for object in Sel:
                xsi.CopyPaste(object,"","DummyRoot")
                nm = object.Name
                object.name = "sv_" + nm
                log("char sv set")
        elif mdlK == "3":
            a = 0
            for object in Sel:
                a += 1
                xsi.CopyPaste(object, "", "DummyRoot")
            log(str(a) + " character model(s) set")
            
def remEx_OnClicked():
    log("removing models from DummyRoot")
    oPPG = PPG.Inspected(0)
    
    delM = oPPG.Parameters("delMdl").Value
    sR = Application.ActiveProject.ActiveScene.Root.Children
    if "DummyRoot" in sR:
        if delM == True:
            a = 0
            dR = getChildren( "DummyRoot" )
            for chld in dR:
                xsi.CopyPaste( chld.Name,"","Scene_Root",1 )
                a += 1
            xsi.CopyPaste("bone_root","","DummyRoot")
            log(str(a) + " models cut from DummyRoot")
        elif delM == False:
            xsi.CopyPaste("bone_root","","DummyRoot",1)
            dR = getChildren( "DummyRoot" )
            for chld in dR:
                xsi.DeleteObj( chld.Name )
                a += 1
            log(str(a) + " models deleted from DummyRoot")
    else:
        log( "DummyRoot doesnt exist." )
                
def mdlKind_OnChanged():
    oPPG = PPG.Inspected(0)
    
    ovrCnt = oPPG.Parameters("overrideCount")
    delEx = oPPG.Parameters("delExst")
    mdlK = oPPG.Parameters("mdlKind").Value
    
    if mdlK == "1":
        ovrCnt.SetCapabilityFlag( 2 , False )
        delEx.SetCapabilityFlag( 2 , False )
    elif mdlK == "2":
        ovrCnt.SetCapabilityFlag( 2 , True )
        delEx.SetCapabilityFlag( 2 , False )
    elif mdlK == "3":
        ovrCnt.SetCapabilityFlag( 2 , True )
        delEx.SetCapabilityFlag( 2 , True )

def groupBones_OnClicked( ):
    log("Grouping bones")
    bones = getBoneList()
    if bones == False:
        log("No Bones existing.")
    else:
        xsi.CreateGroup("Bones", bones)
        log("bones grouped")
    
def toggleBoneVis_OnClicked( ):
    log("Hiding/Unhiding bones")
    bones = getBoneList()
    if bones == False:
        log("No Bones existing.")
    else:
        xsi.ToggleVisibility(bones)
        log("hid/unhid bones")
    
#####################################################################################
#####################################################################################
##general dynamic methods
def Close_OnClicked():
    PPG.Close()
    xsi.DeleteObj('ZETools')
def getBoneList( ):
    log("getting bone list")
    xsifact = win32com.client.Dispatch( "XSI.Factory" )
    oColl = xsifact.CreateObject( "XSI.Collection" )
    oColl.items = "bone*"
    
    if oColl.Count >= 1:
        boneList = []
        a = 0
        for element in oColl:
            boneList.append(element)
            a += 1
        return boneList
        log("returned bone list with " + str(a) + " bones)")
    else:
        return False
        log("No bones existing")
        
def getChildren( objName ):
    log("Getting DummyRoot children")
    sR = Application.ActiveProject.ActiveScene.Root.Children
    for chld in sR:
        if chld.Name == objName:
            return chld.Children
            log("returned children")
                
def checkExistence( objName ):
    log("checking existence of " + str(objName))
    xsifact = win32com.client.Dispatch( "XSI.Factory" )
    oColl = xsifact.CreateObject( "XSI.Collection" )
    oColl.items = objName
    
    if oColl.Count == 1:
        log( "found 1 model" )
        return True
    elif oColl.Count > 1:
        log("found multiple")
        return "multi"
    else:
        log("found none")
        return False
    
def templateImport(tS,tN):#tS is templateSort('C'haracter,'V'ehicle,'W'eapon), tN is the selection value
    log("importing template")
    templateList = getTemplateList(tS)
    if templateList == []:
        log( "No Templates existing." )
    else:
        log(templateList[tN-1])#selection value - 1 because python counts from 0, xsi selections begin with 1
        toImp = templateList[tN-1]#index(?) needs to be specified twice > need another object
        xsi.importDotXSI( addonpath + "\\XSIZETools\\Resources\\Templates\\" + toImp[:-1] + ".xsi")#last 2 chars need to be ignored, are \n(newline)
        log("imported " + str(toImp[:-1]))
    
    
def getTemplateList( arg1 ):#arg1 = templateSort, check templateImport
    log("getting template list")
    #variables for template storage
    charTemplates = []
    vehTemplates = []
    weapTemplates = []
    ctc = 0
    vtc = 0
    wtc = 0
    #get templates from templates file
    templateFile = open(str(addonpath + "\\XSIZETools\\Resources\\Templates\\templates.tcnt"), "r")
    for line in templateFile:
        if line[:1] == "#":
            pass
        elif line[:1] == "c":
            ctc += 1
            charTemplates.append(line[2:])
        elif line[:1] == "v":
            vtc += 1
            vehTemplates.append(line[2:])
        elif line[:1] == "w":
            wtc += 1
            weapTemplates.append(line[2:])
    templateFile.close()
    
    if arg1 == "c": #returns the needed list
        log("return char templates")
        return charTemplates
    elif arg1 == "v":
        log("return vehicle templates")
        return vehTemplates
    elif arg1 == "w":
        log("return weapon templates")
        return weapTemplates
        
def log( text ): #superfast way of Application.LogMessage("text")
    xsi.LogMessage(text)
    
def checkSel():
    log("checking selection")
    slctn = xsi.Selection
    if slctn.Count == 0:
        newSel = popExplorer()
        return newSel
    else:
        return slctn
        
def popExplorer():
    log("transient explorer is badass")
    Sel = xsi.OpenTransientExplorer("",0,1)
    return Sel
