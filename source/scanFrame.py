"""
Created on Tue Aug  3 11:50:01 2021

@author: graceluo

Construct scan frame
"""

import tkinter as tk
from tkinter import ttk
from scanList import scanList
#from bnpScan import bnpScan, 
from pvComm import pvComm
from scanBNP import xrfSetup, scanStart, scanFinish, getCoordinate, getMotorList
from logger import stdoutToTextbox
import time, datetime
import pandas as pd

class scanFrame():
    
    def checkUserDir(self):
        if self.pvComm.getDir() != self.pvComm.userdir:
            self.pvComm = pvComm()
            
    def updateRecord(self):
        self.slist.sclist.item(self.record, text='', 
                               values = tuple(self.recordval))
    
    def scanClick(self):
        if self.scan_btn['state'] == tk.ACTIVE:
            self.scan_btn['state'] = tk.DISABLED
            self.scanclick = True
    
    def scanSetup(self):
        self.record, self.recordval = self.slist.searchQueue()
        if self.record is not None:
            self.pause_btn['state'] = tk.NORMAL
            self.slist.pbarInit()
            self.scan_start_time = 0
            self.scdic = {u:self.recordval[i] for i, u in enumerate(self.slist.sclist_col)}
            self.scdic.update({'bda':float(self.bda.get())})
            self.checkUserDir()
            self.stype = self.scdic['scanType']
            self.recordval[0] = self.pvComm.nextScanName()
            self.coordsReady = False
            
            if self.stype =='Coarse':
                self.coarse_scnum = self.recordval[0]
            
            if self.stype == 'Fine':
                self.checkFineScanCoord()
            else:
                self.coordsReady = True
                self.motors = xrfSetup(self.pvComm, self.scdic) # return a list of tuples
                self.monitormsg.set('wait for motors to be ready')
            self.pending = True
        else:
            self.scanclick = False
            self.scan_btn['state'] = tk.NORMAL
            self.pause_btn['state'] = tk.DISABLED
            self.monitormsg.set('Not scanning, not active')
        
    
    def updateXYZcoor(self, fine_corr):
        for i, s_ in enumerate(['x_scan', 'y_scan']):
            self.scdic[s_] = fine_corr[i]
            self.recordval[self.slist.sclist_col.index(s_)] = '%.2f'%(fine_corr[i])
        self.updateRecord()
    
    def checkFineScanCoord(self):
        fine_coor = getCoordinate(self.pvComm, self.coarse_scnum, 
                                  self.scdic)
        if fine_coor is not None:
            self.updateXYZcoor(fine_coor)
            self.motors = xrfSetup(self.pvComm, self.scdic)
            self.coordsReady = True
            self.pending = True
        else:
            self.monitormsg.set('Waiting for coordinates for fine scans')
    
    def checkMotorReady(self):
        # Add timeout parameters
        if len(self.motors) > 0:
            mn, mv, mt = self.motors[0]
            act = '%s_Act'%mn
            rqs = '%s_Rqs'%mn
            self.pvComm.assignSinglePV(rqs, mv)
            mready = self.pvComm.motorReady(mn, mt)
            if mready == 1:
                self.motors.pop(0)
        else:
            self.pvComm.setXYcenter()
            self.pvComm.centerPiezoXY()
            time.sleep(0.5)
            self.pvComm.centerPiezoXY()
            time.sleep(0.5)
            xztp_ready = self.pvComm.motorReady_XZTP()
            motor_diff = self.pvComm.sumMotorDiff(getMotorList(self.scdic))
            print('Motor difference: %.2f'%(motor_diff))
            MOTOR_DIFF_MIN = 0.5
            if (xztp_ready) & (motor_diff < MOTOR_DIFF_MIN):
                self.motorReady = 1
            else:
                self.motors = getMotorList(self.scdic)
    
    def scanDone(self, *args, **kwargs):
        if self.scandone_var.get():
            scanFinish(self.pvComm, float(self.bda.get()))
            self.recordval[1] = 'done'
            self.updateRecord()
            self.motorReady = 0
            self.pbarscval.set(1)
            self.slist.pbarInit()
            self.scan_start_time = 0
            self.scandone_var.set(False)
    
    def scanExec(self):
        scanStart(self.pvComm, float(self.bda.get()))
        # if status:
        self.pbarscval.set(0.0)
        self.monitormsg.set('Motor ready')
        time.sleep(0.5)
        self.pending = False
        self.monitormsg.set('scanning')
        self.recordval[1] = 'scanning'
        self.updateRecord()
        self.pvComm.pvs['run'].pv.put(1)
        self.scanning = True
        # else:
        #     # self.monitormsg.set('Fail to center XY piezo motors... tyring again')
        #     print('Fail to center XY piezo motors... batch scan paused... check piezo motors')
        #     self.pauseClick()

    def scanMonitor(self, *args, **kwargs):
        ms = 1000
        
        if self.pause & self.scanning:
            if self.pvComm.pvs['wait_val'].pv.value == 0:
                self.pvComm.scanPause()
                self.monitormsg.set('Scan Pause with 1 wait flag, waiting for current line to finish')
                
            elif self.pvComm.pvs['msg1d'].pv.get() == 'SCAN Complete':
                self.abort_btn['state'] = tk.NORMAL
                self.abortall_btn['state'] = tk.NORMAL
                self.resume_btn['state'] = tk.NORMAL  
        
        # when pause and not scanning 
        
        elif self.pause & self.motorReady: pass
        elif self.pause & self.coordsReady: pass
    
        elif not self.pause:
            self.abortall_btn['state'] = tk.DISABLED
            if self.scanclick & self.pending:
                if not self.coordsReady:
                    self.checkFineScanCoord()
                    ms = 2000
                elif not self.motorReady:
                    self.checkMotorReady()
                else:
                    self.scanExec()
                        
            elif self.scanclick & (not self.pending) & (not self.scanning):
                self.monitormsg.set('look for next scan')
                self.scanSetup()
                
            elif self.scanning:
                if not self.pvComm.pvs['pause'].pv.value:
                    self.monitormsg.set('scanning')
                    if self.scan_start_time == 0: 
                        self.scan_start_time = datetime.datetime.now()
                        self.det_reset_attemp = 0
                        self.cline = 0
                    self.pbarUpdate()
                    self.checkDetectorStatus()
                    self.logTempPV()
                    self.monitormsg.set('Scanning... will be done at: %s'%self.eta_str)
                else:
                    self.monitormsg.set('scan is paused or has started yet... check end station shutter')
                
                if self.pvComm.pvs['run'].pv.value == 0:
                    self.scanning = False
                    self.scandone_var.set(True)
                
        self.mmsg_label.after(ms, self.scanMonitor)
        
    def logTempPV(self):
        if self.logTemp.get():
            self.pvComm.logCryoTemp()

    def pbarUpdate(self):
        cline = self.pvComm.pvs['cur_lines'].pv.value
        tline = self.pvComm.pvs['tot_lines'].pv.value
        time_delta = datetime.datetime.now() - self.scan_start_time
        timePerLine = (time_delta.seconds) / float((cline+1))
        remain_st = timePerLine*(tline-cline)
        eta_time = pd.Timestamp.now() + pd.DateOffset(minutes = self.slist.getTotalTime(remaining_st=remain_st))
        self.eta_str = eta_time.strftime('%Y-%m-%d %X')
        self.pbarscmsg.set('%s [%d / %d] %.1f %%remaining' % (self.recordval[0],
                           cline, tline, 100-cline/tline*100))
        self.pbarscval.set(cline/tline*100)
        
    def checkDetectorStatus(self):
        if self.detectorMonitor.get():
            exec_status = self.pvComm.pvs["run"].pv.value
            pause_status = self.pvComm.pvs["pause"].pv.value
            wait_status = self.pvComm.pvs["wait"].pv.value
            cline = self.pvComm.pvs["cur_lines"].pv.value
            det_sec = round(self.pvComm.pvs["det_time"].pv.value, 2)
            self.single_line_time = self.pvComm.pvs['1D_time'].pv.value
            # factor = 3
            extra = 10
            if cline > self.cline:
                self.cline = cline
                self.det_reset_attemp = 0
            elif all([exec_status, not pause_status, not wait_status,
                    (extra + self.single_line_time) < det_sec, 
                    self.det_reset_attemp < 5]):
                self.monitormsg.set('Scan hungs... Resetting detector')
                print('Scan hungs... Resetting detector')
                self.pvComm.scanPause()
                det_reset_status = self.pvComm.resetDetector()
                if det_reset_status < 0: self.pvComm.resetDetector()
                if self.pvComm.pvs['wait'].pv.value > 0: self.pvComm.scanResume()
                self.det_reset_attemp += 1
    
            elif self.det_reset_attemp > 5:
                self.monitormsg.set('Scan hungs... Reach detector reset limit... Need to try reset manually, Or other issues')
                print('Scan hungs... Reach detector reset limit... Need to try reset manually')
            else:
                print('line %d: detector elaspe time %.2f, reset when time larger than %.2f, number of attamp: %d'%(self.cline, det_sec, extra+self.single_line_time, self.det_reset_attemp))


    def pauseClick(self):
        print('Pause scan thread pressed')
        self.pause = True
        self.pause_btn['state'] = tk.DISABLED
        if not self.scanning:
            self.resume_btn['state'] = tk.NORMAL
            self.abort_btn['state'] = tk.NORMAL
        
    def resumeClick(self):
        print('Resume scan thread pressed')
        self.pause_btn['state'] = tk.NORMAL
        self.resume_btn['state'] = tk.DISABLED
        self.abort_btn['state'] = tk.DISABLED
        self.abortall_btn['state'] = tk.DISABLED
        self.pause = False

        if self.scanning:
            self.pvComm.scanResume()

    
    def abortSingleClick(self):
        print('Abort single clicked, aborting current scan')
        self.abort_btn['state'] = tk.DISABLED
        self.resume_btn['state'] = tk.DISABLED
        self.abortall_btn['state'] = tk.DISABLED
        self.pause = False
        self.pause_btn['state'] = tk.NORMAL
        # self.abortsingle = True
        if self.scanning:
            self.pvComm.scanAbort()
            self.pvComm.scanResume()
            self.scanning = False
            self.scandone_var.set(True)
            self.recordval[1] = 'abort'
            self.updateRecord()
        elif (not self.scanning) & (not self.abortall):
            self.recordval[1] = 'abort'
            self.updateRecord()
            self.pending = False
            self.scanSetup()

        # else:


    
    def abortAllClick(self):
        print('Abort all clicked')
        self.abortall = True
        self.abortSingleClick()

        self.abortall = False
        self.scanclick = False
        self.pending = False
        self.coordsReady = 0
        self.motorReady = 0
        self.pause = False
        self.abortall_btn['state'] = tk.DISABLED
        self.scan_btn['state'] = tk.NORMAL
        self.pause_btn['state'] = tk.DISABLED
    

    
    def __init__(self, tabControl, setup_tab):
        self.scanfrm = ttk.Frame(tabControl)
        self.inputs_labels = setup_tab.inputs_labels
        self.calctime_out = setup_tab.calctime_out
        self.scanType = setup_tab.scanType
        self.smp_name = setup_tab.smp_name
        self.bda = setup_tab.bda
        self.tot_time = setup_tab.tot_time
        self.scanParms = setup_tab.scanParms
        self.scan_start_time = 0
        self.eta_str = ''
        self.cline = 0
        self.det_reset_attemp = 0
        self.cline_time = 0
        self.single_line_time = 0
        self.slist = scanList(self.scanfrm, self.inputs_labels, self.calctime_out,
                 self.scanType, self.smp_name, self.bda, self.tot_time, self.scanParms)
        self.insertScan = self.slist.insertScan

        self.scanclick = False
        self.pause = False
        self.abortsingle = False
        self.abortall = False
        self.pending = False
        self.scanning = False
        self.coordsReady = 0
        self.coarse_scnum = ''
        self.motorReady = 0
        self.scdic = None
        self.stype = 'XRF'
        self.motors = []
        self.scandone_var = tk.BooleanVar()
        self.scandone_var.set(False)
        self.scandone_var.trace('w', self.scanDone)
        self.record = None
        self.recordval = None
        self.parm = {}
        self.pvComm = pvComm()
        
        self.pbarscmsg = tk.StringVar()
        self.pbarscmsg.set('%s'%(self.pvComm.nextScanName()))
        pbar_sc_txt = tk.Label(self.scanfrm, textvariable = self.pbarscmsg)
        pbar_sc_txt.grid(row = 23, column = 5, sticky='w', pady = (35, 0),
                             padx = (20,0))
        self.pbarscval = tk.DoubleVar()
        self.pbarscval.set(0.0)
        self.pbar_sc = ttk.Progressbar(self.scanfrm, orient = tk.HORIZONTAL, 
                                           length = 300, mode = 'determinate',
                                           variable = self.pbarscval)
        self.pbar_sc.grid(row = 23, column = 5, columnspan = 3, sticky='w', 
                              pady = (35,0), padx=(290,0))
        
        self.monitormsg = tk.StringVar()
        self.monitormsg.set('Not scanning, not active')
        self.mmsg_label = tk.Label(self.scanfrm, textvariable = self.monitormsg)
        self.mmsg_label.grid(row = 24, column = 1, columnspan = 5, padx=(20,0),
                             sticky = 'w')
        
        self.detectorMonitor = tk.IntVar()
        self.detectorMonitor.set(0)
        detMonitor_btn = ttk.Checkbutton(
            master=self.scanfrm, text='Detector Monitor', variable=self.detectorMonitor)
        detMonitor_btn.grid(row=24, column=5)
        
        
        self.scmsg = tk.Text(self.scanfrm, wrap = 'word', height = 15, width = 152)
        self.scmsg.grid(row = 24, column = 1, sticky = 'w', columnspan = 5, 
                        rowspan = 8, padx=(20,0), pady=(5,0))
        stdoutToTextbox(self.scmsg)
        
        row = 23
        clearsclist_btn = tk.Button(self.scanfrm, text = 'Clear all', command = self.slist.clearSclist, width = 20)
        clearsclist_btn.grid(row=row, column=0, sticky='w', pady=(15,0), padx=(20,0))
        
        rmselect_btn = tk.Button(self.scanfrm, text = 'Remove selected', command = self.slist.removeSelect, width = 20)
        rmselect_btn.grid(row=row+1, column=0, sticky = 'w', pady=(15,0), padx=(20,0))
        
        self.scan_btn = tk.Button(self.scanfrm, text = 'Scan', command = self.scanClick, width = 20)
        self.scan_btn.grid(row=row+2, column=0, sticky = 'w', pady = (15, 0), padx=(20,0))
        
        self.pause_btn = tk.Button(self.scanfrm, text = 'Pause', command = self.pauseClick, width = 20)
        self.pause_btn.grid(row=row+3, column=0, sticky = 'w', pady = (15, 0), padx=(20,0))
        self.pause_btn['state'] = tk.DISABLED
        
        self.resume_btn = tk.Button(self.scanfrm, text = 'Resume', command = self.resumeClick, width = 20)
        self.resume_btn.grid(row =row+4, column = 0, sticky = 'w', pady = (15, 0), padx=(20,0))
        self.resume_btn['state'] = tk.DISABLED
        
        self.abort_btn = tk.Button(self.scanfrm, text = 'Abort Single Scan', command = self.abortSingleClick, width = 20)
        self.abort_btn.grid(row =row+5, column = 0, sticky = 'w', pady = (15, 0), padx=(20,0))
        self.abort_btn['state'] = tk.DISABLED
        
        self.abortall_btn = tk.Button(self.scanfrm, text = 'Abort Batch', command = self.abortAllClick, width = 20)
        self.abortall_btn.grid(row =row+6, column = 0, sticky = 'w', pady = (15, 0), padx=(20,0))
        self.abortall_btn['state'] = tk.DISABLED
        
        self.logTemp = tk.IntVar()
        logTemp_chckbx = tk.Checkbutton(self.scanfrm, text = 'Log Temperature',
                                        variable = self.logTemp, width = 20)
        logTemp_chckbx.grid(row =24, column = 5, padx=(300,0))
        
        try:
            self.mmsg_label.after(1000, self.scanMonitor)
        except:
            pass

