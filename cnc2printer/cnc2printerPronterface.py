##This is a pronterface python plugin that converts cnc gcode
## to printer/marlin gcode so that printerface and RAMPS can be 
## used for milling

## One macro need to be deined in pronterface to execute the code
##  Be sure to remove the # comments when creating the macro
## Cnc2printer macro

#!lib="C:/Users/Ryan/Programs/Pronterface/"
#!import sys
#!addpath=True
#!for libpath in sys.path:
#!    if libpath.startswith(lib):
#!        addpath=False
#!if addpath:
#!    print "Adding path", lib
#!    sys.path.append(lib)
#!try:
#!    import cnc2printerPronterface
#!    reload(cnc2printerPronterface)
#!except Exception, error:
#!    print error
#!print "Loaded"
#!cnc2printerPronterface.cnc2printerMacro(self).convert()
#!cnc2printerPronterface.cnc2printerMacro(self, offset=True, zOffset=-0.28).convert()


import wx
import cnc2printer
reload(cnc2printer)
import os

class cnc2printerMacro(cnc2printer.cnc2printer):
    def __init__(self, parent, shift=False, center=True, offset=False, zOffset=0):
        cnc2printer.cnc2printer.__init__(self, parent, shift=shift, center=center, offset=offset, zOffset=zOffset)
        self.last_path = "C:/Users/Ryan/Documents/3dStlFiles/"
        self.inputFilename = ""
        self.outputFilename = ""

    def loadFiles(self):
        result=""

        basedir = self.last_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir = os.path.split(self.filename)[0]
            except:
                pass

        dlg = wx.FileDialog(self.parent, _("Open file to translate"), 
                          basedir, style = wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        option = " GCODE files (*.gcode;*.gco;*.g;*.ngc;)|"
        option += "*.gcode;*.gco;*.g;*.ngc;|All Files (*.*)|*.*"
        dlg.SetWildcard(_(option))
        if(dlg.ShowModal() == wx.ID_OK):
            result = dlg.GetPath()
        return result

    def convert(self):
        self.parent.clearOutput("")
        try:
            self.inputFilename = self.loadFiles()
            if not self.inputFilename:
                print "No File specified" 
                return
        except Exceptiom, error:
            print error

        if self.inputFilename:
            res = self.inputFilename.split(".")
            self.outputFilename = res[0] + "_convert.gcode"
            self.last_path = os.path.dirname(self.inputFilename)

        self.convertFile(self.inputFilename, self.outputFilename)

try:
    cnc2printerSingleton=None
except Exception, error:
    print "Exception", error

def GetCnc2printerSingleton(parent):
    global cnc2printerSingleton
    if not cnc2printerSingleton:
        cnc2printerSingleton=cnc2printerMacro(parent)
    return cnc2printerSingleton


