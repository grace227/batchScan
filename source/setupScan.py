"""
Created on Wed Jul 28 14:32:26 2021

@author: graceluo

Function to setup scan, interact with PV mostly
"""
import time, os, sys
from epics import caput, caget
import numpy as np
from imgProcessing import getROIcoordinate, getElmMap, getROIcoordinate_data
from tqdm import tqdm

from pvObjects import getPVobj
from logger import logger
from misc import getCurrentTime


class scanControl():
    def __init__(self, userdir = None, logfile = 'log.txt'):
        self.pvs = getPVobj()
        if userdir is None:
            self.userdir = self.getDir()
        else:
            self.userdir = userdir
        self.logfilepath = os.path.join(self.userdir, logfile)
        self.logger = logger(self.logfilepath)
        for k, v in getPVobj.items(): v.logger = self.logger
        self.scandic = {}
            
    def getDir(self):
        fs = self.pvs['filesys'].pv.value
        fs = fs.replace('//micdata/data1', '/mnt/micdata1')
        return os.path.join(fs, self.pvs['subdir'].pv.value.replace('mda', ''))
    
    def changeTomoRotate(self, theta):
        curr_angle = self.pvs['tomo_rot_Act'].pv.value
        t = getCurrentTime()
        self.logger.write('%s; Changing tomo rotation angle from to %.2f to %.2f\n'%(t, curr_angle, theta))
        self.pvs['tomo_rot_Act'].pv.put_callback(theta)
    
    def changeSMRotate(self, theta):
        curr_angle = self.pvs['sm_rot_Act'].curr_value
        t = getCurrentTime()
        self.logger.write('%s; Changing sample rotation angle from to %.2f to %.2f\n'%(t, curr_angle, theta))
        self.pvs['sm_rot_Act'].pv.put_callback(theta)
    
    def blockBeamBDA(self):
        bda_pos = self.scandic['BDAin'] - 500
        t = getCurrentTime()
        self.logger.write('%s: Move BDA to block position at: %.3f\n'%(t, bda_pos))
        self.pvs['BDA_pos'].pv.put_callback(bda_pos)
        
    def openBeamBDA(self):
        bda_pos = self.scandic['BDAin']
        self.logger.write('%s: Move BDA to open position at: %.3f\n'%(getCurrentTime(), bda_pos))
        self.pvs['BDA_pos'].pv.put_callback(bda_pos)
    
    def changeXYcombinedMode(self):        
        self.logger.write('%s; Changing XY scan mode to combined motion\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put_callback(0)
        self.pvs['y_motorMode'].pv.put_callback(0)
        
    def changeXtoPiezolMode(self):
        self.logger.write('%s: Changing X scan mode to Piezo only\n'%(getCurrentTime()))
        self.pvs['x_motorMode'].pv.put_callback(2)
        time.sleep(1.)

    def setXYcenter(self):
        self.logger.write('%s: Update the current position as the center of'\
                    'the scan.\n'%(getCurrentTime()))
        self.pvs['x_setcenter'].pv.put_callback(1)
        self.pvs['y_setcenter'].pv.put_callback(1)
        
    def centerPiezoXY(self):
        self.logger.write('%s: Centering piezoX and piezoY.\n'%(getCurrentTime()))
        self.pvs['piezo_xCenter'].pv.put_callback(1)
        self.pvs['piezo_ycenter'].pv.put_callback(1)
    
    def assignPosValToPVs(self, pvstr, pvval):
        for s_, v_ in zip(pvstr, pvval):
            self.pvs[s_].pv.put_callback(v_)
            self.logger('%s: Change %s to %.3f\n' % (getCurrentTime(), s_, v_))
    
    def motorReady(self, label, mtolerance):
        self.logger.write('%s: Checking whether motors are ready.\n'%(getCurrentTime()))
        rules = [0] * len(label)
        for i, (l, t) in enumerate(zip(label, mtolerance)):
            actpv = self.pvs['%s_Act'%l].pv
            rqspv = self.pvs['%s_Rqs'%l].pv
            self.pvs['%s_Act'%l].motorReady(rqspv.pv, t**2)
            if self.pvs['%s_Act'%l].motor_ready:
                self.logger.write('%s: %s motor is in position with value'\
                                '%.2f\n'%(getCurrentTime(), l, actpv.value))
                rules[i] = 1
            else:
                self.logger.write('%s: %s motor not in position, current: %.2f,'\
                                ' request: %.2f\n'%(getCurrentTime(), l, actpv.value, rqspv.value))
        if all(rules):
            self.logger.write('%s: Motors ready\n'%getCurrentTime())
            return 1
        else:
            return 0
         
    def fileReady(self, next_sc, filepath, time_lim):
        # Wait until file exists
        while not os.path.exists(filepath):
            time.sleep(1)

        time_diff = 0
        while (time_diff < time_lim):
            time.sleep(1)
            file_mod_time = os.stat(filepath).st_mtime
            time_diff = int(time.time() - file_mod_time)
            sys.stdout.write('Waiting for coarse scan file %s to be ready,'\
                             ' file modified time: %d, time difference: %d \n'\
                             %(next_sc, file_mod_time, time_diff))
            
    def imgProgFolderCheck(self):
        img_path= os.path.join(self.userdir,'imgProg')
        if not os.path.exists(img_path):
            os.makedirs(img_path)
        return img_path
    
    def nextScanName(self):
        return '%s%s.mda'%(caget(self.pvs['basename']), 
                           str(caget(self.pvs['nextsc'])).zfill(4))
    
    def execScan(self, scname, scidx, n_scns, pbar):
        self.setXYcenter()
        self.changeXtoPiezolMode()
        self.centerPiezoXY()
        self.openBeamBDA()
        
        # Execute Scan
        caput(self.pvs['run'], 1)
        self.logger('%s: Scanning \n'%(getCurrentTime()))
        if pbar is None:
            self.logProgress(scname, scidx = scidx, 
                             n_scns = n_scns) 
      
    def logTemp(self):
        logpvs = ['CryoCon1:In_3', 'CryoCon1:In_2', 
                  'CryoCon3:In_2', 'CryoCon3:Loop_2', 
                  'CryoCon1:In_1']
        msg = getCurrentTime() + ': '
        cline = caget(self.pvs['cur_lines'])
        msg += '%d, '%(cline)
        for lpv in logpvs:
            msg += '%.3f, '%(caget(self.pvs[lpv]))
        msg += '\n'
        self.logger_logbook_only(msg)
        
    def detPauseStart(self):
        print('try reset detector')
        
    
    def logProgress(self, scname, scidx = 0, n_scns = 1, 
                    pbarval = None, pbarmsg = None, logTemp = False):
        
        nlines = caget(self.pvs['tot_lines'])
        tic = time.perf_counter()
        tic1 = tic
        scmonitor_tic = tic
        
        with tqdm(total = nlines, desc = '%s (%d/%d)'%(scname, scidx, n_scns)) as pbar:
            pbar.update(caget(self.pvs['cur_lines']))
        
            while caget(self.pvs['run']):
                toc = time.perf_counter()
                
                if logTemp & ((toc-tic1) >= 1):
                    self.logTemp()
                    tic1 = toc
                
#                if (toc - scmonitor_tic) < (caget(self.pvs['det_time']) / 10):
#                    print('in scan monitor')
#                    print(toc - scmonitor_tic)
#                    self.detPauseStart()
#                    scmonitor_tic = toc

                elif (toc-tic) >=10:
    #             time.sleep(10)
                    cline = caget(self.pvs['cur_lines'])
                    self.updatePbar(pbar, scname, 
                                    pbarval = pbarval, 
                                    pbarmsg = pbarmsg,
                                    cline = cline, 
                                    nlines = nlines)
                    pbar.update(cline-pbar.n)
#                     sys.stdout.write('Scanning %s (batch %d/%d): line %d/%d is done\n'\
#                                      %(scname, scidx+1, n_scns, cline, nlines))
                    tic = toc

            self.updatePbar(pbar, scname, pbarval = pbarval, 
                            pbarmsg = pbarmsg, done = 1)
            pbar.update(nlines)

        self.logger('%s: Finish scan: %s%s'%(getCurrentTime(), scname, '\n'*3))
        self.blockBeamBDA()
        self.changeXYcombinedMode
    
    def updatePbar(self, pbar, scname, pbarval = None, pbarmsg = None, 
                   cline = 0, nlines = 1, done = 0):
        
        if done & (pbarval is not None):
            pbarval.set(100)
        elif pbarval is not None:
            pbarval.set(cline/nlines*100)
            
        if pbarmsg is not None:
            msg_pbar = str(pbar)
            m = msg_pbar[msg_pbar.index('['):msg_pbar.index(']')+1]
            pbarmsg.set('%s %s'%(scname, m))
    
    def fineScanInit(self, params_label, params, scname, scidx, n_scns, pbar):
        self.blockBeamBDA()
        self.changeXYcombinedMode()
        self.assignPosValToPVs(params_label, params)

        # Check following motor to see if they are in position
        label = ['x_center', 'y_center', 'z_value', 'sm_rot']
        mtolerance = [0.1, 0.1, 0.5, 0.2]
        self.motorReady(label, mtolerance)
        self.execScan(scname, scidx, n_scns, pbar)
        
    def batchXRFInit(self, params_label, params, scname, scidx, n_scns, pbar):
        self.blockBeamBDA()
        self.changeXYcombinedMode()
        
        if self.scandic['batchXRF_fixAngle']['smp_angle'] is not None:
            self.changeSMRotate(self.scandic['batchXRF_fixAngle']['smp_angle'])
            
        self.assignPosValToPVs(params_label, params)
        label = ['x_center', 'y_center', 'z_value']
        mtolerance = [0.1, 0.1, 0.5]
        self.motorReady(label, mtolerance)
        self.execScan(scname, scidx, n_scns, pbar)
    
    def angleSweepScanInit(self, params_label, params, scname, scidx, n_scns, pbar):
        self.blockBeamBDA()
        self.changeXYcombinedMode()
        
        self.logger('%s: Putting Tomo angle rotation back to 0 deg\n'%(getCurrentTime()))
        self.changeTomoRotate(0) # initialize angle at 0 deg
        time.sleep(1)
        
        self.assignPosValToPVs(params_label[:-1], params[:-1])
        self.motorReady(['x_center', 'y_center', 'z_value'], [0.1, 0.1, 0.5])
        self.changeTomoRotate(params[-1]) # change to desired angle
        self.motorReady(['x_center', 'z_value'], [0.1, 0.5])
        self.execScan(scname, scidx, n_scns, pbar)
    
    def coarseFineScanInit(self, params_label, params, scname, 
                           scidx, n_scns, scan_setting, pbar, 
                           skipCoarse = False):
        if not skipCoarse:
            self.angleSweepScanInit(params_label, params, 
                                    scname, scidx, n_scns, pbar)
        
        # If find_bbox is on, perform image processing on the coarse scan to get coordinates
        if scan_setting['find_bbox']:
            cscan_path = os.path.join(self.userdir, 'img.dat/%s.h5'%(scname))
            time_lim = 10  #sec
            self.fileReady(scname, cscan_path, time_lim)
            img_path = self.imgProgFolderCheck()   
            figpath = os.path.join(img_path, 'bbox_%s.png'%(scname))
            
            if scan_setting['use_mask']:
                maskmap = getElmMap(cscan_path, scan_setting['elm_mask'])[0]
                mask = maskmap < (np.mean(maskmap) + scan_setting['n_std']*np.std(maskmap.ravel()))
                m1 = getElmMap(cscan_path, self.scandic['elm'])
                elmmap = m1[0] * mask
                new_x, new_y, new_w, new_h = getROIcoordinate_data(elmmap, m1[1], m1[2],  
                                                  n_cluster = scan_setting['n_cluster'],
                                                  sel_cluster = scan_setting['sel_cluster'],
                                                  figpath = figpath)
            else:
                new_x, new_y, new_w, new_h = getROIcoordinate(cscan_path, 
                                                              self.scandic['elm'],
                                                              n_cluster = scan_setting['n_cluster'],
                                                              sel_cluster = scan_setting['sel_cluster'],
                                                              figpath = figpath)
            f_scanparm = scan_setting['fine_pts_area']
            
#             ##TODO: implement checkROIIntensity function
#             proceed = checkROIIntensity(cscan_path, self.scandic['elm'], 
#                                         [new_x, new_y, f_scanparm[0], f_scanparm[1]])
            proceed = 1
            
            if proceed:
                self.logger('%.2f(width) \n %.2f(height)\n'%(new_w, new_h))
                curr_smz = caget(self.pvs['z_value_Rqs'])
                scan_ = params[-1]
                params = []
                f_scanparm = scan_setting['fine_pts_area']
                params = f_scanparm + [scan_] + [new_x, new_y, curr_smz]
                flabels = ['x_width', 'y_width', 'x_step', 'y_step', 'dwell', 'sm_rot_Rqs',
                              'x_center_Rqs','y_center_Rqs', 'z_value_Rqs']

                next_sc = self.nextScanName(caget(self.pvs['fname_saveData']))
                self.logger('%s Initiating fine scan %s %s\n'%('#'*20, next_sc, '#'*20))
                self.logger('Sample temp (K): %.3f\n'%(caget(self.pvs['temp'])))
                self.fineScanInit(flabels, params, next_sc, scidx, n_scns, pbar)

            else:
                self.logger('Extracted ROI appears to have intensity below average,'\
                            ' suggesting a no feature region.\n Aborting the batch scan. \n')
                ##TODO: send out an email if this happen
                status = -1  # Flag to terminate batch scan
    
    def getXYZBbox(self, scname, elm, n_cluster=2, sel_cluster = 1,
                time_lim = 10, use_mask = False, elm_mask = 'P', 
                n_std = 2):
        cscan_path = os.path.join(self.userdir, 'img.dat/%s.h5'%(scname))
        time_lim = time_lim  #sec
        self.fileReady(scname, cscan_path, time_lim)
        img_path = self.imgProgFolderCheck()   
        figpath = os.path.join(img_path, 'bbox_%s.png'%(scname))
            
        if use_mask:
            maskmap = getElmMap(cscan_path, elm_mask)[0]
            mask = maskmap < (np.mean(maskmap) + n_std*np.std(maskmap.ravel()))
            m1 = getElmMap(cscan_path, elm)
            elmmap = m1[0] * mask
            new_corr = getROIcoordinate_data(elmmap, m1[1], m1[2],  
                                              n_cluster = n_cluster,
                                              sel_cluster = sel_cluster,
                                              figpath = figpath)
        else:
            new_corr = getROIcoordinate(cscan_path, elm,
                                        n_cluster = n_cluster,
                                        sel_cluster = sel_cluster,
                                        figpath = figpath)
            
        return new_corr[0], new_corr[1], self.getXYZcenter()[-1]

    
    def getXYZcenter(self):
        return [caget(self.pvs[i]) for i in ['x_center_Act', 'y_center_Act', 'z_value_Act']]
    

