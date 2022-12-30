from pvObjects import getPVobj
from misc import getCurrentTime
import os, time, sys
import numpy as np

class pvComm():

    """This is a class that handles epics communication
    """

    def __init__(self, userdir = None, log = 'log.txt'):
        """Constructor method, initializing the working directory and creating a log file

        Parameters
        ----------
        userdir : str, optional
            userdir is the path of the working directory
        log: str, optional
            log is the filename of the log file. Log file contains the machine status during scans
        """

        self.pvs = getPVobj()
        if userdir is None:
            self.userdir = self.getDir()
        else:
            self.userdir = userdir
        self.logfilepath = os.path.join(self.userdir, log)
        self.logfid = open(self.logfilepath, 'a')
            
    def logger(self, msg):
        """The function outputs and writes msg in both GUI text field or log file

        Parameters
        ----------
        msg : str
            Text message to be outputted or logged in GUI interface or log file. 
        """
        sys.stdout.write(msg)
        sys.stdout.flush()
        if self.logfid.closed:
            self.logfid = open(self.logfilepath, 'a')
        self.logfid.write(msg)
        self.logfid.flush()
    
    def getDir(self):
        """The function gets the current working directory.
        Involved PV ::
            9idbBNP:saveData_fileSystem
        """
        fs = self.pvs['filesys'].pv.value
        fs = fs.replace('//micdata/data1', '/mnt/micdata1')
        return os.path.join(fs, self.pvs['subdir'].pv.value.replace('mda', ''))
    
    def getBDAx(self):
        """The function gets the current BDA motor position. 
        Involved PV ::
            9idbTAU:UA:UX:RqsPos
        """
        return np.round(self.pvs['BDA_pos'].pv.value, 2)
    
    def getSMAngle(self):
        """The function gets the current sample rotation. 
        Involved PV ::
            9idbTAU:SM:ST:ActPos
        """
        return np.round(self.pvs['sm_rot_Act'].pv.value, 2)
    
    def getTomoAngle(self):
        """The function gets the current sample rotation. 
        Involved PV ::
            9idbTAU:SM:CT:ActPos
        """
        return np.round(self.pvs['tomo_rot_Act'].pv.value, 2)
    
    def scanPause(self):
        """The function increases the following PV by 1.
        Involved PV ::
            9idbBNP:scan2.WAIT
        """
        self.pvs['wait'].put_callback(1)
    
    def scanResume(self):
        """The function decreases the following PV by 1.
        Involved PV ::
            9idbBNP:scan2.WAIT
        """
        self.pvs['wait'].put_callback(0)
        
    def scanAbort(self):
        """The function assigns the following PV to 1.
        Involved PV ::
            9idbBNP:AbortScans.PROC
        """
        self.pvs['abort'].put_callback(1)
        
    def resetDetector(self):
        """The function resets XRF detector if it hangs. 
        Involved PVs ::
            netCDF file write   --> 9idbXMAP:netCDF1:WriteFile
            netCDF file capture --> 9idbXMAP:netCDF1:Capture
            MCS stop            --> 9idbBNP:3820:StopAll
            XMAP stop           --> 9idbXMAP:StopAll
        
        Returns
          -------
          float
            1 if successful or -1 when reset fails
        """
        print('check netCDF status: current status is %s'%(self.pvs['netCDF_status'].pv.get(as_string=True)))
        if self.pvs['netCDF_status'].pv.get(as_string=True) == 'Writing':
            print('Save current netCDF data and stop file write')
            self.pvs['netCDF_save'].pv.put(1)
            time.sleep(0.1)
            self.pvs['netCDF_stp'].pv.put(1)
        self.pvs['mcs_stp'].pv.put(1)
        self.pvs['xmap_stp'].pv.put(1)
        time.sleep(0.2)
        if self.detectorDone():
            self.scanResume()
            return 1
        else:
            return -1
        
    def detectorDone(self):
        """The function checks if XMAP or MCS are in the idle mode. 
        Involved PVs ::
            MCS status  --> 9idbBNP:3820:Acquiring
            XMAP status --> 9idbXMAP:Acquiring
        
        Returns
          -------
          boolean
            True if idle; False when either XMAP or MCS is active
        """
        xmap_done = self.pvs['xmap_status'].pv.value
        mcs_done = self.pvs['mcs_status'].pv.value
        if all([not xmap_done, not mcs_done]):
            return False
        else:
            return True
        
    def logCryoTemp(self):
        """The function logs temperatures in units of K.
        Involved PVs ::
            CryoCon1:In_1   --> 9idbCRYO:CryoCon1:In_1:Temp.VAL
            CryoCon1:In_3   --> 9idbCRYO:CryoCon1:In_3:Temp.VAL
            CryoCon1:In_2   --> 9idbCRYO:CryoCon1:In_2:Temp.VAL
            CryoCon3:In_2   --> 9idbCRYO:CryoCon3:In_2:Temp.VAL
            CryoCon3:Loop_2 --> 9idbCRYO:CryoCon3:Loop_2:SetControl.VAL
        """
        temp_pv = ['CryoCon1:In_1', 'CryoCon1:In_2', 'CryoCon1:In_3', 'CryoCon3:In_2', 'CryoCon3:Loop_2']
        s = ['%s: %.2f'%(t, self.pvs[t].pv.value) for t in temp_pv]
        s = ', '.join(s)
        msg = getCurrentTime() + ': ' + s + '\n'
        self.logger('%s'%msg)
    
    def changeTomoRotate(self, theta):
        """The function rotates sample to the desired angle during tomographic data collection.
        Involved PV ::
            9idbTAU:SM:CT:ActPos
        
        Parameters
        ----------
        theta : float
            Target angle of sample rotation 
        """
        curr_angle = np.round(self.pvs['tomo_rot_Act'].pv.value, 2)
        t = getCurrentTime()
        self.logger('%s; Changing tomo rotation angle from to %.2f to %.2f\n'%(t, curr_angle, theta))
        self.pvs['tomo_rot_Act'].put_callback(theta)
    
    def changeSMRotate(self, theta):
        """The function rotates sample to the desired angle.
        Involved PV ::
            9idbTAU:SM:ST:ActPos
        
        Parameters
        ----------
        theta : float
            Target angle of sample rotation 
        """
        curr_angle = np.round(self.pvs['sm_rot_Act'].curr_value, 2)
        t = getCurrentTime()
        self.logger('%s; Changing sample rotation angle from to %.2f to %.2f\n'%(t, curr_angle, theta))
        self.pvs['sm_rot_Act'].put_callback(theta)
    
    def blockBeamBDA(self, BDA):
        """The function move BDA by 500 um, relative to its IN positon, to block the incident X-ray beam.
        Involved PV ::
            9idbTAU:UA:UX:RqsPos
            
        Parameters
        ----------
        BDA : float
            Motor position of BDA when it is in the beam path 
        """
        bda_pos = BDA - 500
        t = getCurrentTime()
        self.logger('%s: Move BDA to block position at: %.3f\n'%(t, bda_pos))
        self.pvs['BDA_pos'].put_callback(bda_pos)
        
    def openBeamBDA(self, BDA):
        """The function move BDA to its IN positon.
        Involved PV ::
            9idbTAU:UA:UX:RqsPos
            
        Parameters
        ----------
        BDA : float
            Motor position of BDA when it is in the beam path 
        """
        self.logger('%s: Move BDA to open position at: %.3f\n'%(getCurrentTime(), BDA))
        self.pvs['BDA_pos'].put_callback(BDA)
    
    def changeXYcombinedMode(self):     
        """The function change the x- and y- motor combined motion (coarse + piezo).
        Involved PV ::
            x motor mode --> 9idbTAU:SM:Ps:xMotionChoice.VAL = 0
            y motor mode --> 9idbTAU:SY:Ps:yMotionChoice.VAL = 0
        """
        self.logger('%s; Changing XY scan mode to combined motion\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put(0)
        self.pvs['y_motorMode'].pv.put(0)
        
    def changeXtoCombinedMode(self):    
        """The function change the x-motor combined motion (coarse + piezo).
        Involved PV ::
            x motor mode --> 9idbTAU:SM:Ps:xMotionChoice.VAL = 0
        """
        self.logger('%s; Changing XY scan mode to combined motion\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put(0) 
        
    def changeXtoPiezolMode(self):
        """The function change the x-motor to piezo mode.
        Involved PV ::
            x motor mode --> 9idbTAU:SM:Ps:xMotionChoice.VAL = 2
        """
        self.logger('%s: Changing X scan mode to Piezo only\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put(2)

    def setXYcenter(self):
        """The function udpates the current x- and y- motor position as the center of a scan.
        Involved PV ::
            x-scan record --> 9idbBNP:scan1.P1CP = 9idbTAU:SM:PX:RqsPos
            y-scan record --> 9idbBNP:scan2.P1CP = 9idbTAU:SY:PY:RqsPos
        """
        self.logger('%s: Update the current position as the center of'\
                    'the scan.\n'%(getCurrentTime()))
        x_rqs = self.pvs['x_center_Rqs'].pv.get()
        y_rqs = self.pvs['y_center_Rqs'].pv.get()
        self.pvs['x_updatecenter'].pv.put(round(x_rqs, 2))
        self.pvs['y_updatecenter'].pv.put(round(y_rqs, 2))
        self.logger('%s: X_center valute: %.2f \n'%(getCurrentTime(), x_rqs))
        self.logger('%s: Y_center valute: %.2f \n'%(getCurrentTime(), y_rqs))
        # self.pvs['x_setcenter'].pv.put(1)
        # self.pvs['y_setcenter'].pv.put(1)
        
    def motorReady_XZTP(self):
        """The function checks if XZTP motor is ready
        Involved PV ::
            9idbTAU:SM:Ps:Ready
            
        Returns
          -------
          float
            1 if XZTP motor is ready or 0 otherwise
        """
        status = self.pvs['xztp_motor_ready'].pv.get(as_string=True)
        ready = 1 if status == 'Ready' else 0
        return ready
        
    # def sumMotorDiff(self, motorlist):
    #     sum_diff = 0
    #     for m in motorlist:
    #         sum_diff += abs(self.pvs['%s_Rqs'%m[0]].pv.get() - self.pvs['%s_Act'%m[0]].pv.get())
    #     return sum_diff
    
    
    def centerPiezoXY(self):
        """The function centers the x- and y- piezo motor
        Involved PV ::
            piezo x-center --> 9idbTAU:SM:Ps:xCenter.PROC
            piezo y-center --> 9idbTAU:SY:Ps:yCenter.PROC
            
        Returns
          -------
          float
            1 if motor is ready or 0 otherwise
        """
        MAX_WAIT_TIME = 5  #sec
        self.logger('%s: Centering piezoX and piezoY.\n'%(getCurrentTime()))
        self.pvs['piezo_xCenter'].pv.put(1)
        self.pvs['piezo_yCenter'].pv.put(1)
        self.logger('%s: Piezo xcenter value: %.2f\n'%(getCurrentTime(), self.pvs['x_piezo_val'].pv.get()))
        self.logger('%s: Piezo ycenter value: %.2f\n'%(getCurrentTime(), self.pvs['y_piezo_val'].pv.get()))
        tin = time.time()
        t_diff = 0
        while (not self.motorReady_XZTP()) & (t_diff < MAX_WAIT_TIME):
            self.logger('%s: Waiting for XZTPX to be ready.\n'%(getCurrentTime()))
            t_diff = time.time() - tin
            time.sleep(0.2)
        
        return self.motorReady_XZTP()
    
    def assignPosValToPVs(self, pvstr, pvval):
        """The function assigns values to PVs 
        Involved PV ::
            piezo x-center --> 9idbTAU:SM:Ps:xCenter.PROC
            piezo y-center --> 9idbTAU:SY:Ps:yCenter.PROC
            
        Parameters
        ----------
        pvstr : list
            A list that holds keys of pvname
        pvval: list
            A list that holds the values of the PVs in pvstr
        """
        for s_, v_ in zip(pvstr, pvval):
            self.pvs[s_].pv.put(v_)
            self.logger('%s: Change %s to %.3f\n' % (getCurrentTime(), s_, v_))
            
    def assignSinglePV(self, pvstr, pvval):
        self.pvs[pvstr].pv.put(pvval)
        self.logger('%s: Change %s to %.3f\n' % (getCurrentTime(), pvstr, pvval))
            
#     def writeScanInit(self, mode, smpinfo, scandic):
#         next_sc = self.nextScanName()
#         self.logger('%s Initiating scan %s %s\n'%('#'*20, next_sc, '#'*20))
#         self.logger('Sample info: %s\n'% smpinfo)
#         self.logger('%s: Setting up scan using %s mode.\n'%(getCurrentTime(), mode))
#         self.logger('%s: %s'%(getCurrentTime(), scandic))
#         self.logger('\n\n')
        
#     def motorReady(self, l, mt):
#         self.logger('%s: Checking whether motors are ready.\n'%(getCurrentTime()))
#         actpv = self.pvs['%s_Act'%l].pv
#         rqspv = self.pvs['%s_Rqs'%l].pv
#         self.pvs['%s_Act'%l].motorReady(rqspv, mt)
        
#         if self.pvs['%s_Act'%l].motor_ready:
#             self.logger('%s: %s motor is in position with value'\
#                             '%.2f\n'%(getCurrentTime(), l, actpv.value))
#             return 1
#         else:
#             self.logger('%s: %s motor not in position, current: %.2f,'\
#                             ' request: %.2f\n'%(getCurrentTime(), l, actpv.value, rqspv.value))
#             return 0
    
#     def nextScanName(self):
#         return '%s%s.mda'%(self.pvs['basename'].pv.value, 
#                            str(self.pvs['nextsc'].pv.value).zfill(4))
    
#     def getXYZcenter(self):
#         return [np.round(self.pvs[i].pv.value, 2) for i in ['x_center_Act', \
#                 'y_center_Act', 'z_value_Act']]
        

    

    

