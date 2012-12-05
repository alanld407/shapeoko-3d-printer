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
import re

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
// M115	- Capabilities string
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


class CodeBase(object):
    def __init__(self, code=None):
        self.data = []
        self.comment = None
        self.code = code
        self.scaleX = 15
        self.scaleY = 15
        self.scaleZ = 1
        self.offsetX = 100
        self.offsetY = 100
        self.offsetZ = 0

    def parseData(self, line):
        raise Exception("parseData not defined")
    
    def parseComment(self, line):
        result = line.split("(")
        if len(result) == 1:
            command, self.comment = result[0], None
        elif len(result) == 2:
            command, self.comment = result[0], "{" + result[1]
        return command, self.comment
    
    def serialize(self):
        raise Exception("serialize not defined")

class NotImplementedCode(CodeBase):
    '''
        This will eat codes that are not implemented in marlin
    '''
    def __init__(self, code=None):
        CodeBase.__init__(self, code)
        #print "Not implemented"

    def parseData( self, s_line ):
        #print "Parse data", self.code, s_line
        self.data.append( s_line )
        
    def serialize(self):
        #print "Not wriiten to File", self.data
        return None

class CoordinateCode(CodeBase):
    def __init__(self, code=None):
        CodeBase.__init__(self, code)
        #print "Not implemented"

    def parseData( self, s_line ):
        #print "Parse data", s_line
        self.data.append( s_line )
        
    def serialize(self):
        result=None
        for cmd in self.data:
            #result += cmd + "\n"
            result = cmd + "\n"
        return result

class CommandCode(CodeBase):
    def __init__(self, code=None):
        CodeBase.__init__(self, code)
        #print "Not implemented"

    def parseData( self, s_line ):
        line = s_line.strip()
        self.data.append( line )
        
    def serialize(self):
        result=""
        for cmd in self.data:
            result += str(self.code) + " " + str(cmd) + "\n"
        return result
        
class GCodeComment(CodeBase):
    def __init__(self, code=";"):
        CodeBase.__init__(self, code)
        
    def parseData( self, line ):
        cmd, comment = self.parseComment(line)
        self.data.append( line )

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
        self.x = None
        self.y = None
        self.z = None
        self.e = 0.0
        
    def parseData( self, line ):
        cmd, comment = self.parseComment(line)
        data = cmd.split(" ")
        code = data[0]
        for i in data:
            if i.startswith("X"):
                self.x = float(i[1:])
            elif i.startswith("Y"):
                self.y = float(i[1:])
            elif i.startswith("Z"):
                self.z = float(i[1:])
            elif i.startswith("E"):
                self.e = float(i[1:])
        result = (self.x, self.y, self.z, self.e)
        self.data.append( result )

    def serialize(self):
        result="G92 E0 (Added to set the amount of Filament)\n"
        #result=""
        for cmd in self.data:
            #print cmd
            #result += cmd + "\n"
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

class GCode1(GCode0):
    def __init__(self, code="G1"):
        GCode0.__init__(self, code)
        self.scaleZ = .1
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

class MCode3(CommandCode):
    '''
        M3 - Turn on Spindle -> M107 Turn on Fan
    '''
    def __init__(self, code="M3"):
        CommandCode.__init__(self, code)

    def parseData( self, s_line ):
        line = s_line.strip()
        self.data.append( line )
        
    def serialize(self):
        result = str("M106") + " (Tuen on Fan/Spindle)\n"
        return result
    
class MCode4(CommandCode):
    '''
        M4 - Turn Off Spindle -> M107 Turn Off Fan
    '''
    def __init__(self, code="M4"):
        CommandCode.__init__(self, code)

    def parseData( self, s_line ):
        #print "Parse data", s_line
        line = s_line.strip()
        self.data.append( line )
        
    def serialize(self):
        result = str("M107") + " (Tuen off Fan/Spindle)\n"
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
        
    def serialize(self):
        result = str(self.code) + " (Override cold extrude)\n"
        return result
    
factoryLookups = {
    ";":GCodeComment,
    "G0":GCode0,
    "G1":GCode1,
    "G04":CommandCode,
    "G21":NotImplementedCode, 
    "G40":NotImplementedCode,�
    "G49":NotImplementedCode,�
    "G54":NotImplementedCode, 
    "G61":NotImplementedCode, #exact path mode
    "G80":NotImplementedCode, #cancel modal motion�
    "G90":GCode90,
    "G91":GCode91,
    "F":NotImplementedCode,  #
    "S":NotImplementedCode,  #
    "M302":MCode302,         # Marlin: Enable Cold Extrudes
    "M2":NotImplementedCode, # End Program
    "M3":MCode3,             # Start Spindle -> M106 Fan On
    "M5":MCode4,             # Stop Spindle -> M107 Fan Off
    
    "P3":NotImplementedCode,
    
    "T1":NotImplementedCode, #
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
            if verbose:
                print "Found GCode 04"
        elif line.startswith("G21"):
            s_gCode = "G21"
            if verbose:
                print "Found GCode 21"
        elif line.startswith("G40"):
            s_gCode = "G40"
            if verbose:
                print "Found GCode 40"
        elif line.startswith("G49"):
            s_gCode = "G49"
            if verbose:
                print "Found GCode 49"                
        elif line.startswith("G54"):
            s_gCode = "G54"
            if verbose:
                print "Found GCode 54"                
        elif line.startswith("G61"):
            s_gCode = "G61"
            if verbose:
                print "Found GCode 61"                
        elif line.startswith("G80"):
            s_gCode = "G80"
            if verbose:
                print "Found GCode 80"                
        elif line.startswith("G90"):
            s_gCode = "G90"
            if verbose:
                print "Found GCode 90"                
        elif line.startswith("G49"):
            s_gCode = "G49"
            if verbose:
                print "Found GCode 49"
        elif line.startswith("G0"):
            s_gCode = "G0"
            if verbose:
                print "Found GCode 0"
        elif line.startswith("G1"):
            s_gCode = "G1"
            if verbose:
                print "Found GCode 1"
        else:
            if verbose:
                print "Found GCode", line
    elif line.startswith("F"):
        s_gCode = "F"
        if verbose:
            print "Found FCode"
    elif line.startswith("M"):
        if line.startswith("M2"):
            s_gCode = "M2"
            if verbose:
                print "Start Spindle"
        elif line.startswith("M3"):
            s_gCode = "M3"
            if verbose:
                print "Start Spindle"
        elif line.startswith("M5"):
            s_gCode = "M5"
            if verbose:
                print "Found MCode 5"
        else:
            if verbose:
                print "Found MCode", line
    elif line.startswith("P"):
        if line.startswith("P3"):
            s_gCode = "P3"
            if verbose:
                print "Start Spindle"
        else:
            if verbose:
                print "Found MCode", line
    elif line.startswith("S"):
        s_gCode = "S"
        if verbose:
             print "Found SCode"
    elif line.startswith("T"):
        if line.startswith("T1"):
            s_gCode = "T1"
            if verbose:
                print "Found TCode 1"
        elif line.startswith("T2"):
            s_gCode = "T2"
            if verbose:
                print "Found TCode 2"
        elif line.startswith("T3"):
            s_gCode = "T3"
            if verbose:
                print "Found TCode 3"
        else:
            if verbose:
                print "Found TCode", line

    return s_gCode

class Cnc2printer(object):
    def __init__(self, parent):
        self.parent = parent
        self.inputFilename  = "C:/Users/Ryan/Documents/3dStlFiles/cylinder/cylinder_v1.ngc"
        self.outputFilename = "C:/Users/Ryan/Documents/3dStlFiles/cylinder/cylinder_convert.gcode"
        self.x = None
        self.y = None
        self.z = None
        
    def convert(self):
        self.parent.clearOutput("")
        
        print self.inputFilename
        try:
            ifp=open(self.inputFilename, "r")
        except:
            print "Failed to open", self.inputFilename

        print self.outputFilename
        try:
            ofp=open(self.outputFilename, "w")
        except:
            print "Failed to open", self.outputFilename
            
        gCode = None
        oldGcode = None
        commandCue = []
        gCodeI = None

        ##Override Cold Extrudes for CNC
        commandCue.append(MCode302())
        
        for s_line in ifp.readlines():
            line = s_line
            if line:
                while line[-1] != ";" and line[-1] != "]" and line[-1] != ")" and not line[-1].isalnum():
                    #print line
                    line = line[:-1]

            try:
                s_gCode = gCodeLookup(line)
                if s_gCode == "G54":
                    print "Found (%s)" % s_gCode, factoryLookups.get(s_gCode)
                    print factoryLookups.keys()
            except:
                print line
                import traceback
                traceback.print_stack()
                raise

            if oldGcode != s_gCode:
                gCodeI = factoryLookups.get(s_gCode, CommandCode)(s_gCode)
                commandCue.append(gCodeI)
                
                #Remove the code from the line
                if s_gCode != ";":
                    line = line[len(s_gCode):]
                    
                while line[0].isspace():
                    line = line[1:]

            if gCodeI:
                gCodeI.parseData(line)
                
            oldCode = s_gCode
        ifp.close()


        
        print "Outputing File", self.outputFilename
        #print commandCue
        for gObj in commandCue:
            cmd = gObj.serialize()
            if cmd:
                ofp.write( str(cmd) )

        print "Done Outputing File", self.outputFilename
        ofp.close()

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

