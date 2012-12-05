##This is a pronterface python plugin that probes across the hotbed and
## prints the Z offsets from the home position
## This requires that you are using the hot end as the endstop

## One macro need to be deined in pronterface to execute the code
##  Be sure to remove the # comments when creating the macro
## Bedlevel macro
#!lib="C:/Users/Ryan/Programs/Pronterface/"
#!import sys
#!addpath=True
#!for libpath in sys.path:
#!    if libpath.startswith(lib):
#!        addpath=False
#!if addpath:
#!    print "Adding path", lib
#!    sys.path.append(lib)

#!import bedlevel
#!reload(bedlevel)
#!bedlevel= bedlevel.Bedleveling(self)
#!bedlevel.level()




import time, sys, threading

mappingCoordinates = [
            (0, 0), (96, 0), (192, 0),
            (192, 180),(96, 180), (0, 180),
            ]

class Bedleveling(object):
    def __init__(self, parent):
        self.parent=parent
        self.fan = False
        
    def sendCmd(self, cmd, stopMsg=None, timeOut=10000000):
        try:
            ##Redirect output from marling until probing is done
            tmpsys=sys.stdout
            sys.stdout = open('nul', 'w')
            
            self.parent.p.send_now( cmd )
            _LastLine = _CurrentLastLine = _TimeOutCounter = 0
            #self.parent.p.clear = True
            while(True):
                _TimeOutCounter += 1
                _CurrentLastLine = self.parent.p.log[-1]
                _LastLine = self.parent.p.log[-2]
                if (stopMsg):
                    if(_LastLine.startswith(stopMsg) and _CurrentLastLine.startswith('ok')):
                        break
                else:
                    if(_CurrentLastLine.startswith('ok')):
                        break
                if _TimeOutCounter>timeOut:
                    break;
            ##Restore stdout
            sys.stdout=tmpsys
            return (_LastLine, _CurrentLastLine)
        except Exception, error:
            print "Error: sendCmd:", error
        finally:
            ##Restore stdout
            sys.stdout=tmpsys
            
    def SamplePoint(self): 
        _LastLine = _CurrentLastLine = _TimeOutCounter = 0
        _LastLine = self.parent.p.log[-1]
        #self.parent.p.send_now("G92 Z4")
        self.parent.p.send_now("G1 Z-8 F60")
        #self.parent.p.clear = True
        while(True):
            _CurrentLastLine = self.parent.p.log[-1]
            if(_CurrentLastLine is not _LastLine and not _CurrentLastLine.startswith('ok')):
                break
        _CurrentLastLine = _CurrentLastLine.replace("echo:endstops","").replace("hit:","").replace("Z:","").replace(" ","").replace("\n","")
        self.parent.p.send_now('G92 Z{0}'.format(float(_CurrentLastLine)))
        self.parent.p.send_now('c'.format(1+float(_CurrentLastLine)))
        return _CurrentLastLine


    def getEndstop(self):
        #print "getEndstop"
        try:
            result = {}
            _LastLine, _CurrentLastLine = self.sendCmd("M119", 'x_min:')

            #print "getEndstop Done: '%s' '%s'" %(_CurrentLastLine[:-1], _LastLine[:-1])
            data = _LastLine[:-2].split(" ")
            for val in data:
                axis, value = val.split(":")
                result[axis] = value 
            return result
        except Exception, error:
            print "getEndstop:Exception", error
            
    def getPosition(self):
        #print"getPosition"
        try:
            result = {}
            _LastLine, _CurrentLastLine = self.sendCmd("M114", 'X:')


            #print "getPosition Done: '%s' '%s'" %(_CurrentLastLine[:-1], _LastLine[:-1])
            datastr = _LastLine
            datastr = datastr.replace("Y", ",Y")
            datastr = datastr.replace("Z", ",Z")
            datastr = datastr.replace("E", ",E")
            
            data = datastr.split(" ")
            posData = data[0].split(",")
            for val in posData:
                axis, value = val.split(":")
                result[axis] = value 

            return result
        except Exception, error:
            print "getPosition:Exception", error
            
    def move(self, offset, axis="Z", dist='relative', feed=260):
        if dist=='relative':
            _LastLine, _CurrentLastLine = self.sendCmd("G91")
        _LastLine, _CurrentLastLine = self.sendCmd("G1 "+axis+str(offset)+" F"+str(feed))
        if dist=='relative':
            _LastLine, _CurrentLastLine = self.sendCmd("G90")

    def moveX(self, offset, dist='relative', feed=260):
        self.move(offset, axis="X", dist=dist, feed=feed)
        
    def moveY(self, offset, dist='relative', feed=260):
        self.move(offset, axis="Y", dist=dist, feed=feed)

    def moveZ(self, offset, dist='relative', feed=260):
        self.move(offset, axis="Z", dist=dist, feed=feed)
        
    def homeAll(self):
        #print "home All"
        try:
            ##Raise Z by 1mm
            #_LastLine, _CurrentLastLine = self.sendCmd("G1 Z1 F320")
            self.moveZ( 4, dist='absolute' )
            ##Home XYZ
            _LastLine, _CurrentLastLine = self.sendCmd("G28")
        except Exception, error:
            print "homeAll Exception", error
        
    def resetZ(self, newz):
        self.sendCmd("G92 Z%s" % (newz,))
        return 0
    
    def findZ(self):
        #Make sure that we have zeroed out the endstops G28
        #Move the endstop 2mm above the surface G1 Z2 F60
        #Remap the enddstop to be 1mm above the surface so that we can test for negative numbers
        #     by setting G92 Z1
        #Nudge the endstop down .1mm at a time by taking the current position and subtracting .1mm
        #   and then test the endstop until we make contact
        #G91
        #G1 Z1
        #G90
        #self.
        #Note: we need to keep track of how far we moved so that we can reset the endstop for the next probe
        _LastLine = _CurrentLastLine = _TimeOutCounter = 0
        _InitialHeightAboveBed = 2
        _TimeOutLimit = 75
        report = []

        ##Clear the proterface output port
        self.parent.clearOutput("")
        print "Leveling"
        
        #self.moveZ(2)
        self.homeAll()
        self.moveZ(_InitialHeightAboveBed)
        self.resetZ(4)

        for x, y in mappingCoordinates:
            _TimeOutCounter = 0
            self.moveX( x, dist='absolute', feed=6000 )
            self.moveY( y, dist='absolute', feed=6000 )
            self.moveZ( 4, dist='absolute' )
            time.sleep(1.0)
            while(True):
                time.sleep(0.001)
                _TimeOutCounter += 1
                try:
                    end = self.getEndstop()
                except Exception, error:
                    print "getEndstop Error:", error
                #print "FindZ Data", _TimeOutCounter, pos, end

                if end['z_min'] == "H":
                    print "ZMin Found @%s, %s" %( x, y )
                    break
                
                try:
                    pos = self.getPosition()
                except Exception, error:
                    print error
                    
                offset = float(pos['Z'])-_InitialHeightAboveBed
                self.moveZ( -.05 )
                
                if _TimeOutCounter > _TimeOutLimit:
                    print "ZMin Not Found @%s, %s" %( x, y )
                    break
            ##Log the Offsets so that we can report later
            report.append( ((x, y), offset, pos, end, _TimeOutCounter) )
            print "Offset:%s, Zpos:%s @(%s, %s), Zmin:%s, TimeOut:%s\n" % \
                      ( offset, pos['Z'], x, y, end['z_min'], _TimeOutCounter)
            
            self.moveZ( 4, dist='absolute' )
        
        self.homeAll()
##        print "Offset Report:"
##        for (x, y), offset, zpos, zend, counter in report:
##            print
##            print "Offset:", offset
##            print "FindZ Data Zpos:%s @(%s, %s), Zmin:%s, TimeOut:%s" % \
##                      ( zpos['Z'], x, y, zend['z_min'], counter)
        print "Bedevel done"
        
    def level(self):

        self.parent.p.loud=False
        try:
            child = threading.Thread(target=self.findZ)
            child.setDaemon(True)
            child.start()
        except Exception, error:
            print error

    def toggleFan(self):
        self.fan = not self.fan
        if self.fan:
            print "Turn Fan On"
            self.sendCmd("M106")
        else:
            print "Turn Fan Off"
            self.sendCmd("M107")


try:
    bedlevelSingleton=None
except Exception, error:
    print "Exception", error

def GetBedlevelSingleton(parent):
    global bedlevelSingleton
    if not bedlevelSingleton:
        bedlevelSingleton=Bedleveling(parent)

    return bedlevelSingleton
        
#if __name__ == '__main__':
##if True:
##    print
##    print "Start Processing"
##    print dir()
##    main = Bedleveling(self)
##    main.level()

