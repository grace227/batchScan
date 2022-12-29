from pvObjects import getPVobj
from misc import getCurrentTime
import os, time, sys
import numpy as np

class pvComm():

    """This is a class that handles epics communication
    """

    def __init__(self, userdir = None, log = 'log.txt'):
        """Constructor method, initializing the working directory and creating a log file
        :param userdir: path of the working directory
        :type userdir: string, optional
	:param log: filename of the log file
	:type log: string, optional
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
        :param msg: text message
        :type msg: string, required
        """
        sys.stdout.write(msg)
        sys.stdout.flush()
        if self.logfid.closed:
            self.logfid = open(self.logfilepath, 'a')
        self.logfid.write(msg)
        self.logfid.flush()
    
    def getDir(self):
        fs = self.pvs['filesys'].pv.value
        fs = fs.replace('//micdata/data1', '/mnt/micdata1')
        return os.path.join(fs, self.pvs['subdir'].pv.value.replace('mda', ''))
    
    def getBDAx(self):
        return np.round(self.pvs['BDA_pos'].pv.value, 2)
    
    def getSMAngle(self):
        return np.round(self.pvs['sm_rot_Act'].pv.value, 2)
    
    def getTomoAngle(self):
        return np.round(self.pvs['tomo_rot_Act'].pv.value, 2)
    
    def scanPause(self):
        self.pvs['wait'].put_callback(1)
    
    def scanResume(self):
        self.pvs['wait'].put_callback(0)
        
    def scanAbort(self):
        self.pvs['abort'].put_callback(1)
        
    def resetDetector(self):
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
        
    def logCryoTemp(self):
        temp_pv = ['CryoCon1:In_1', 'CryoCon1:In_2', 'CryoCon1:In_3', 'CryoCon3:In_2', 'CryoCon3:Loop_2']
        s = ['%s: %.2f'%(t, self.pvs[t].pv.value) for t in temp_pv]
        s = ', '.join(s)
        msg = getCurrentTime() + ': ' + s + '\n'
        self.logger('%s'%msg)

    def detectorDone(self):
        xmap_done = self.pvs['xmap_status'].pv.value
        mcs_done = self.pvs['mcs_status'].pv.value
        if all([not xmap_done, not mcs_done]):
            return False
        else:
            return True
    
    def changeTomoRotate(self, theta):
        curr_angle = np.round(self.pvs['tomo_rot_Act'].pv.value, 2)
        t = getCurrentTime()
        self.logger('%s; Changing tomo rotation angle from to %.2f to %.2f\n'%(t, curr_angle, theta))
        self.pvs['tomo_rot_Act'].put_callback(theta)
    
    def changeSMRotate(self, theta):
        curr_angle = np.round(self.pvs['sm_rot_Act'].curr_value, 2)
        t = getCurrentTime()
        self.logger('%s; Changing sample rotation angle from to %.2f to %.2f\n'%(t, curr_angle, theta))
        self.pvs['sm_rot_Act'].put_callback(theta)
    
    def blockBeamBDA(self, BDA):
        bda_pos = BDA - 500
        t = getCurrentTime()
        self.logger('%s: Move BDA to block position at: %.3f\n'%(t, bda_pos))
        self.pvs['BDA_pos'].put_callback(bda_pos)
        
    def openBeamBDA(self, BDA):
        self.logger('%s: Move BDA to open position at: %.3f\n'%(getCurrentTime(), BDA))
        self.pvs['BDA_pos'].put_callback(BDA)
    
    def changeXYcombinedMode(self):        
        self.logger('%s; Changing XY scan mode to combined motion\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put(0)
        self.pvs['y_motorMode'].pv.put(0)
        
    def changeXtoCombinedMode(self):        
        self.logger('%s; Changing XY scan mode to combined motion\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put(0) 
        
    def changeXtoPiezolMode(self):
        self.logger('%s: Changing X scan mode to Piezo only\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put(2)

    def setXYcenter(self):
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
        status = self.pvs['xztp_motor_ready'].pv.get(as_string=True)
        ready = 1 if status == 'Ready' else 0
        return ready
        
    def sumMotorDiff(self, motorlist):
        sum_diff = 0
        for m in motorlist:
            sum_diff += abs(self.pvs['%s_Rqs'%m[0]].pv.get() - self.pvs['%s_Act'%m[0]].pv.get())
        return sum_diff
    
    
    def centerPiezoXY(self):
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
        
        # MAX_WAIT_TIME = 2  #sec
        # t_diff = 0
        # tin = time.time()
        
        # while (self.pvs['xztp_motor_ready'].pv.get(as_string=True) != 'Ready') & (t_diff < MAX_WAIT_TIME):
        #     self.logger('%s: Waiting for piezoX.\n'%(getCurrentTime()))
        #     time.sleep(0.2)
        #     t_diff = time.time() - tin
        # x_status = 1 if self.pvs['xztp_motor_ready'].pv.get(as_string=True) == 'Ready' else 0
        # print(x_status)
            
        # self.pvs['piezo_yCenter'].pv.put(1)
        # t_diff = 0
        # tin = time.time()
        # while (self.pvs['y_motor_ready'].pv.get(as_string=True) != 'Ready') & (t_diff < MAX_WAIT_TIME):
        #     self.logger('%s: Waiting for piezoY.\n'%(getCurrentTime()))
        #     time.sleep(0.2)
        #     t_diff = time.time() - tin
        # y_status = 1 if self.pvs['y_motor_ready'].pv.get(as_string=True) == 'Ready' else 0
        # print(y_status)
        
        # return x_status * y_status

    
    def assignPosValToPVs(self, pvstr, pvval):
        for s_, v_ in zip(pvstr, pvval):
            self.pvs[s_].pv.put(v_)
            self.logger('%s: Change %s to %.3f\n' % (getCurrentTime(), s_, v_))
            
    def assignSinglePV(self, pvstr, pvval):
        self.pvs[pvstr].pv.put(pvval)
        self.logger('%s: Change %s to %.3f\n' % (getCurrentTime(), pvstr, pvval))
            
    def writeScanInit(self, mode, smpinfo, scandic):
        next_sc = self.nextScanName()
        self.logger('%s Initiating scan %s %s\n'%('#'*20, next_sc, '#'*20))
        self.logger('Sample info: %s\n'% smpinfo)
        self.logger('%s: Setting up scan using %s mode.\n'%(getCurrentTime(), mode))
        self.logger('%s: %s'%(getCurrentTime(), scandic))
        self.logger('\n\n')
        
    def motorReady(self, l, mt):
        self.logger('%s: Checking whether motors are ready.\n'%(getCurrentTime()))
        actpv = self.pvs['%s_Act'%l].pv
        rqspv = self.pvs['%s_Rqs'%l].pv
        self.pvs['%s_Act'%l].motorReady(rqspv, mt)
        
        if self.pvs['%s_Act'%l].motor_ready:
            self.logger('%s: %s motor is in position with value'\
                            '%.2f\n'%(getCurrentTime(), l, actpv.value))
            return 1
        else:
            self.logger('%s: %s motor not in position, current: %.2f,'\
                            ' request: %.2f\n'%(getCurrentTime(), l, actpv.value, rqspv.value))
            return 0
    
#    def motorReady(self, label, mtolerance):
#        self.logger('%s: Checking whether motors are ready.\n'%(getCurrentTime()))
#        rules = [0] * len(label)
#        for i, (l, t) in enumerate(zip(label, mtolerance)):
#            actpv = self.pvs['%s_Act'%l].pv
#            rqspv = self.pvs['%s_Rqs'%l].pv
#            self.pvs['%s_Act'%l].motorReady(rqspv, t)
#            if self.pvs['%s_Act'%l].motor_ready:
#                self.logger('%s: %s motor is in position with value'\
#                                '%.2f\n'%(getCurrentTime(), l, actpv.value))
#                rules[i] = 1
#            else:
#                self.logger('%s: %s motor not in position, current: %.2f,'\
#                                ' request: %.2f\n'%(getCurrentTime(), l, actpv.value, rqspv.value))
#            time.sleep(1)
#                
#        if all(rules):
#            self.logger('%s: Motors ready\n'%getCurrentTime())
#            return 1
#        else:
#            return 0         
    
    def nextScanName(self):
        return '%s%s.mda'%(self.pvs['basename'].pv.value, 
                           str(self.pvs['nextsc'].pv.value).zfill(4))
    
    def getXYZcenter(self):
        return [np.round(self.pvs[i].pv.value, 2) for i in ['x_center_Act', \
                'y_center_Act', 'z_value_Act']]
        

    

    

