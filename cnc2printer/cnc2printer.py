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

#!import cnc2printer
#!reload(cnc2printer)
#!cnc2printer= cnc2printer.Cnc2printer(self)
#!cnc2printer.level()

import time, sys, threading
import os
import re
import wx

"""
// look here for descriptions of gcodes: http://linuxcnc.org/handbook/gcode/g-code.html
// http://objects.reprap.org/wiki/Mendel_User_Manual:_RepRapGCodes

//Implemented Codes
//-------------------
// G0  -> G1
// G1  - Coordinated Movement X Y Z E
// G2  - CW ARC
// G3  - CCW ARC
// G4  - Dwell S<seconds> or P<milliseconds>
// G10 - retract filament according to settings of M207
// G11 - retract recover filament according to settings of M208
// G28 - Home all Axis
// G90 - Use Absolute Coordinates
// G91 - Use Relative Coordinates
// G92 - Set current position to cordinates given

//RepRap M Codes
// M0   - Unconditional stop - Wait for user to press a button on the LCD (Only if ULTRA_LCD is enabled)
// M1   - Same as M0
// M104 - Set extruder target temp
// M105 - Read current temp
// M106 - Fan on
// M107 - Fan off
// M109 - Wait for extruder current temp to reach target temp.
// M114 - Display current position

//Custom M Codes
// M17  - Enable/Power all stepper motors
// M18  - Disable all stepper motors; same as M84
// M20  - List SD card
// M21  - Init SD card
// M22  - Release SD card
// M23  - Select SD file (M23 filename.g)
// M24  - Start/resume SD print
// M25  - Pause SD print
// M26  - Set SD position in bytes (M26 S12345)
// M27  - Report SD print status
// M28  - Start SD write (M28 filename.g)
// M29  - Stop SD write
// M30  - Delete file from SD (M30 filename.g)
// M31  - Output time since last M109 or SD card start to serial
// M42  - Change pin status via gcode
// M80  - Turn on Power Supply
// M81  - Turn off Power Supply
// M82  - Set E codes absolute (default)
// M83  - Set E codes relative while in Absolute Coordinates (G90) mode
// M84  - Disable steppers until next move, 
//        or use S<seconds> to specify an inactivity timeout, after which the steppers will be disabled.  S0 to disable the timeout.
// M85  - Set inactivity shutdown timer with parameter S<seconds>. To disable set zero (default)
// M92  - Set axis_steps_per_unit - same syntax as G92
// M114 - Output current position to serial port 
// M115        - Capabilities string
// M117 - display message
// M119 - Output Endstop status to serial port
// M140 - Set bed target temp
// M190 - Wait for bed current temp to reach target temp.
// M200 - Set filament diameter
// M201 - Set max acceleration in units/s^2 for print moves (M201 X1000 Y1000)
// M202 - Set max acceleration in units/s^2 for travel moves (M202 X1000 Y1000) Unused in Marlin!!
// M203 - Set maximum feedrate that your machine can sustain (M203 X200 Y200 Z300 E10000) in mm/sec
// M204 - Set default acceleration: S normal moves T filament only moves (M204 S3000 T7000) im mm/sec^2  also sets minimum segment time in ms (B20000) to prevent buffer underruns and M20 minimum feedrate
// M205 -  advanced settings:  minimum travel speed S=while printing T=travel only,  B=minimum segment time X= maximum xy jerk, Z=maximum Z jerk, E=maximum E jerk
// M206 - set additional homeing offset
// M207 - set retract length S[positive mm] F[feedrate mm/sec] Z[additional zlift/hop]
// M208 - set recover=unretract length S[positive mm surplus to the M207 S*] F[feedrate mm/sec]
// M209 - S<1=true/0=false> enable automatic retract detect if the slicer did not support G10/11: every normal extrude-only move will be classified as retract depending on the direction.
// M220 S<factor in percent>- set speed factor override percentage
// M221 S<factor in percent>- set extrude factor override percentage
// M240 - Trigger a camera to take a photograph
// M301 - Set PID parameters P I and D
// M302 - Allow cold extrudes
// M303 - PID relay autotune S<temperature> sets the target temperature. (default target temperature = 150C)
// M400 - Finish all moves
// M500 - stores paramters in EEPROM
// M501 - reads parameters from EEPROM (if you need reset them after you changed them temporarily).  
// M502 - reverts to the default "factory settings".  You still need to store them in EEPROM afterwards if you want to.
// M503 - print the current settings (from memory not from eeprom)
// M999 - Restart after being stopped by error

//Stepper Movement Variables
"""

global x
global y
global z

class CodeBase(object):
    def __init__(self, code=None):
        self.data = []
        self.comment = None
        self.code = code
        self.x = None
        self.y = None
        self.z = None
        self.e = 1.0
        self.scaleX = 1
        self.scaleY = 1
        self.scaleZ = 1
        self.offsetX = 50
        self.offsetY = 50
        self.offsetZ = 0
        self.min     = [10000.0, 10000.0, 10000.0]
        self.max     = [-10000.0, -10000.0, -10000.0]

    def shiftCoordinates(self, x, y, z):
        pass

    def calculateMinMax(self):
        return None

    def parseCoordinate( self, line ):
        global x
        global y
        global z
        cmd, comment = self.parseComment(line)
        data = cmd.split(" ")
        for i in data:
            if i.startswith("X"):
                x = self.x = float(i[1:])
            elif i.startswith("Y"):
                y = self.y = float(i[1:])
            elif i.startswith("Z"):
                z = self.z = float(i[1:])
            elif i.startswith("E"):
                self.e = float(i[1:])
        return [x, y, z, self.e]

    def parseData(self, line):
        raise Exception("parseData not defined")
    
    def parseComment(self, line):
        result = line.split("(")
        if len(result) == 1:
            command, self.comment = result[0], None
        elif len(result) == 2:
            command, self.comment = result[0], "(" + result[1]
        return command, self.comment
    
    def serialize(self):
        raise Exception("serialize not defined")

class NotImplementedCode(CodeBase):
    '''
        This will eat codes that are not implemented in marlin
    '''
    def __init__(self, code=None):
        CodeBase.__init__(self, code)

    def parseData( self, s_line ):
        self.data.append( s_line )
        return True
        
    def serialize(self):
        result=""
        for cmd in self.data:
            result += ";" + str(self.code) + " " + str(cmd) + "    (Not Implemented)\n"
        return result

class FSCode(NotImplementedCode):
    def __init__(self, code=None):
        NotImplementedCode.__init__(self, code)

    def serialize(self):
        result=""
        for cmd in self.data:
            result += ";" + str(self.code) + str(cmd) + "    (Not Implemented)\n"
        return result
    
class CoordinateCode(CodeBase):
    def __init__(self, code=None):
        CodeBase.__init__(self, code)
        #print "Not implemented"

    def parseData( self, s_line ):
        line = ";" + s_line
        self.data.append( line )
        return True
        
    def serialize(self):
        result=""
        for cmd in self.data:
            result += cmd + "\n"
        return result

class CommandCode(CodeBase):
    def __init__(self, code=None):
        CodeBase.__init__(self, code)

    def parseData( self, s_line ):
        line = s_line.strip()
        cmd, comment = self.parseComment(line)
        self.data.append( (cmd, comment) )
        return True
        
    def serialize(self):
        result=""
        for cmd, comment in self.data:
            result += str(self.code) + " " + str(cmd)
            if comment:
                result += " " + str(comment)
            result += "\n"

        return result

class SingleLineCommandCode(CodeBase):
    def __init__(self, code=None):
        CodeBase.__init__(self, code)

    def parseData( self, s_line ):
        if self.data:
            line = s_line.strip()
            result = self.parseCoordinate( line )
            print line, result
            return False
        line = s_line.strip()
        cmd, comment = self.parseComment(line)
        self.data.append( (cmd, comment) )
        return True
        
    def serialize(self):
        result=""
        for cmd, comment in self.data:
            result += str(self.code) + " " + str(cmd)
            if comment:
                result += " " + str(comment)
            result += "\n"

        return result


############################################################    
## GCodes
############################################################    
class GCodeComment(CodeBase):
    def __init__(self, code=";"):
        CodeBase.__init__(self, code)
        
    def parseData( self, line ):
        cmd, comment = self.parseComment(line)
        self.data.append( line )
        return True

    def serialize(self):
        result=None
        for cmd in self.data:
            result = cmd + "\n"
        return result


class GCode0(CoordinateCode):
    '''
        G0  -> G1
        G1  - Coordinated Movement X Y Z E
    '''
    def __init__(self, code="G0"):
        CoordinateCode.__init__(self, code)
        #Need to supply a little E so that 
        #  pronterface will load an display the gcode

    def shiftCoordinates(self, x, y, z):
        for idx, point in enumerate(self.data):
            ix, iy, iz, e = self.data[idx]
            if ix:
                self.data[idx][0] = ix + x
            else:
                self.data[idx][0] = x
            if iy:
                self.data[idx][1] = iy + y
            else:
                self.data[idx][1] = y
            if iz:
                self.data[idx][2] = iz + z
            else:
                self.data[idx][2] = z

    def calculateMinMax(self):
        fmin = [10000.0, 10000.0, 10000.0]
        fmax = [-10000.0, -10000.0, -10000.0]
        if not self.data:
            return None
        for point in self.data:
            x, y, z, e = point
            if x:
                fmin[0] = min(fmin[0], x)
                fmax[0] = max(fmax[0], x)
            if y:
                fmin[1] = min(fmin[1], y)
                fmax[1] = max(fmax[1], y)
            if z:
                fmin[2] = min(fmin[2], z)
                fmax[2] = max(fmax[2], z)
        return (fmin, fmax)
        
    def parseData( self, line ):
        result = self.parseCoordinate( line )
        self.data.append( result )
        return True

    def serialize(self):
        result="G92 E0 (Added to set the amount of Filament)\n"
        for cmd in self.data:
            lresult = ""
            for axis, val in enumerate(cmd):
                if axis == 0 and val!=None:
                    lresult += " X%s" % (val * self.scaleX + self.offsetX)
                elif axis == 1 and val!=None:
                    lresult += " Y%s" % (val * self.scaleY + self.offsetY)
                elif axis == 2 and val!=None:
                    lresult += " Z%s" % (val * self.scaleZ + self.offsetZ)
                elif axis == 3 and val!=None:
                    lresult += " E%s" % val

            result += self.code + lresult + "\n"

        return result

class GCode4(SingleLineCommandCode):
    def __init__(self, code="G4"):
        SingleLineCommandCode.__init__(self, code)

class GCode04(SingleLineCommandCode):
    def __init__(self, code="G04"):
        SingleLineCommandCode.__init__(self, code)

class GCode1(GCode0):
    def __init__(self, code="G1"):
        GCode0.__init__(self, code)
        self.scaleZ  = 1
        self.offsetZ = 0

class GCode90(CommandCode):
    '''
        G90 - Use Absolute Coordinates
    '''
    def __init__(self, code="G90"):
        CommandCode.__init__(self, code)

class GCode91(CommandCode):
    '''
        G91 - Use Relative Coordinates
    '''
    def __init__(self, code="G90"):
        CommandCode.__init__(self, code)

class GCode92(CommandCode):
    '''
        G92 - Set current position to cordinates given
    '''
    def __init__(self, code="G92"):
        CommandCode.__init__(self, code)

############################################################    
## MCodes
############################################################    
class MCode3(CommandCode):
    '''
        M3 - Turn on Spindle -> M107 Turn on Fan
    '''
    def __init__(self, code="M3"):
        CommandCode.__init__(self, code)

    def parseData( self, s_line ):
        line = s_line.strip()
        self.data.append( line )
        return True
        
    def serialize(self):
        result = str("M106 S255") + " (Turn on Fan/Spindle)\n"
        return result
    
class MCode4(CommandCode):
    '''
        M4 - Turn Off Spindle -> M107 Turn Off Fan
    '''
    def __init__(self, code="M4"):
        CommandCode.__init__(self, code)

    def parseData( self, s_line ):
        line = s_line.strip()
        self.data.append( line )
        return True
        
    def serialize(self):
        result = str("M107 S0") + " (Turn off Fan/Spindle)\n"
        return result


class MCode302(CommandCode):
    '''
        M302 - Allow cold extrudes
    '''
    def __init__(self, code="M302"):
        CommandCode.__init__(self, code)

    def parseData( self, s_line ):
        line = s_line.strip()
        self.data.append( line )
        return True
        
    def serialize(self):
        result = str(self.code) + " (Override cold extrude)\n"
        return result


############################################################    
## Factory
############################################################    
factoryLookups = {
    ";":GCodeComment,
    "G0":GCode0,
    "G1":GCode1,
    "G4":GCode4,
    "G04":GCode04,
    "G21":NotImplementedCode, 
    "G40":NotImplementedCode,
    "G49":NotImplementedCode,
    "G54":NotImplementedCode, 
    "G61":NotImplementedCode, #exact path mode
    "G80":NotImplementedCode, #cancel modal motion
    "G90":GCode90,
    "G91":GCode91,
    "F":FSCode,  #
    "S":FSCode,  #
    "M302":MCode302,         # Marlin: Enable Cold Extrudes
    "M2":NotImplementedCode, # End Program
    "M3":MCode3,             # Start Spindle -> M106 Fan On
    "M5":MCode4,             # Stop Spindle  -> M107 Fan Off
    "M106":MCode3,           # Start Spindle -> M106 Fan On
    "M107":MCode4,           # Stop Spindle  -> M107 Fan Off
    
    "P3":NotImplementedCode,
    
    "T1":NotImplementedCode, #
    "T2":NotImplementedCode, #
    "T3":NotImplementedCode, #
    }

def gCodeLookup(line):
    verbose=False
    s_gCode=None

    if line.startswith(";"):
        gCode = -1
        s_gCode = ";"
    elif line.startswith("G"):
        if line.startswith("G04"):
            s_gCode = "G04"
        elif line.startswith("G21"):
            s_gCode = "G21"
        elif line.startswith("G40"):
            s_gCode = "G40"
        elif line.startswith("G49"):
            s_gCode = "G49"
        elif line.startswith("G54"):
            s_gCode = "G54"
        elif line.startswith("G61"):
            s_gCode = "G61"
        elif line.startswith("G80"):
            s_gCode = "G80"
        elif line.startswith("G90"):
            s_gCode = "G90"
        elif line.startswith("G0"):
            s_gCode = "G0"
        elif line.startswith("G1"):
            s_gCode = "G1"
        elif line.startswith("G4"):
            s_gCode = "G4"
    elif line.startswith("F"):
            s_gCode = "F"
    elif line.startswith("M"):
        if line.startswith("M2"):
            s_gCode = "M2"
        elif line.startswith("M3"):
            s_gCode = "M3"
        elif line.startswith("M5"):
            s_gCode = "M5"
    elif line.startswith("P"):
        if line.startswith("P3"):
            s_gCode = "P3"
    elif line.startswith("S"):
        s_gCode = "S"
    elif line.startswith("T"):
        if line.startswith("T1"):
            s_gCode = "T1"
        elif line.startswith("T2"):
            s_gCode = "T2"
        elif line.startswith("T3"):
            s_gCode = "T3"

    if verbose:
        print "Found Code", s_gCode

    return s_gCode

class Cnc2printer(object):
    def __init__(self, parent):
        self.parent = parent
        self.last_path = "C:/Users/Ryan/Documents/3dStlFiles/"
        self.inputFilename  = ""
        self.outputFilename = ""
        self.x = None
        self.y = None
        self.z = None

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

    def calculateMinMax(self):
        fmin = [10000.0, 10000.0, 10000.0]
        fmax = [-10000.0, -10000.0, -10000.0]
        for gObj in self.commandCue:
            minMax = gObj.calculateMinMax()
            if minMax:
                [xmin, ymin, zmin], [xmax, ymax, zmax] = minMax
                fmin[0] = min(fmin[0], xmin)
                fmin[1] = min(fmin[1], ymin)
                fmin[2] = min(fmin[2], zmin)
                fmax[0] = max(fmax[0], xmax)
                fmax[1] = max(fmax[1], ymax)
                fmax[2] = max(fmax[2], zmax)
        return fmin, fmax


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
        
        print "InputFile", self.inputFilename
        try:
            ifp=open(self.inputFilename, "r")
        except:
            print "Failed to open", self.inputFilename

        print "OutputFile", self.outputFilename
        try:
            ofp=open(self.outputFilename, "w")
        except:
            print "Failed to open", self.outputFilename
            
        gCode = None
        oldGcode = None
        self.commandCue = []
        gCodeI = None

        ##Override Cold Extrudes for CNC
        self.commandCue.append(MCode302())
        
        for s_line in ifp.readlines():
            line = s_line
            if line and len(line) > 1:
                while line[-1] != ";" and \
                      line[-1] != "]" and \
                      line[-1] != ")" and \
                      not line[-1].isalnum():
                    line = line[:-1]

            try:
                s_gCode = gCodeLookup(line)
            except:
                print "Error", line
                import traceback
                traceback.print_stack()
                raise
 
            if s_gCode and oldGcode != s_gCode:
                gCodeI = factoryLookups.get(s_gCode, CommandCode)(s_gCode)
                self.commandCue.append(gCodeI)

                #Remove the code from the line`
                if s_gCode != ";":
                    line = line[len(s_gCode):]
                    
            while line[0].isspace():
                line = line[1:]

            if gCodeI:
                result = gCodeI.parseData(line)
                
            oldGcode = s_gCode
        ifp.close()

        print "Calculating Min/Max"
        fmin, fmax = self.calculateMinMax()
        print fmin, fmax

        print "Shifting Min/Max", -fmin[0], -fmin[1], -fmin[2]
        for gObj in self.commandCue:
            gObj.shiftCoordinates(-fmin[0], -fmin[1], -fmin[2])

        print "Calculating Min/Max"
        fmin, fmax = self.calculateMinMax()
        print fmin, fmax

        print "Outputing File"
        for gObj in self.commandCue:
            cmd = gObj.serialize()
            if cmd:
                ofp.write( str(cmd) )

        print "Done Outputing File", self.outputFilename
        ofp.close()
        self.commandCue=None

try:
    cnc2printerSingleton=None
except Exception, error:
    print "Exception", error

def GetCnc2printerSingleton(parent):
    global cnc2printerSingleton
    if not cnc2printerSingleton:
        cnc2printerSingleton=Cnc2printer(parent)
    return cnc2printerSingleton


        
#if __name__ == '__main__':
##if True:
##    print
##    print "Start Processing"
##    print dir()
##    main = Cnc2printer(self)
##    main.level()

