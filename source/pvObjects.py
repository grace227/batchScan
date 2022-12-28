"""
Created on Wed Oct 27 10:28:14 2021

@author: graceluo

Create and get PVobjects

"""

import epics, sys
import numpy as np
from misc import getCurrentTime

class pvObject(object):
    
    def __init__(self, pv_str, pv_key):
        self.pv = epics.PV(pv_str)
        self.pvname = pv_key
        self.putvalue = self.pv.value
        self.put_complete = 0
        self.motor_ready = 1
            
    def onPutComplete(self, pvname=None,  **kws):
        sys.stdout.write('%s: Finish updating PV %s with value of %s\n'\
                          %(getCurrentTime(), self.pvname, str(self.putvalue)))
        self.put_complete = 1
        
    def put_callback(self, v = None):
        self.put_complete = 0
        if v is not None:
            self.putvalue = v
            self.pv.put(self.putvalue, callback=self.onPutComplete)

    def motorReady(self, rqspv, tolerance = 4e-2):
        rqsvalue = np.round(rqspv.value, 2)
        if abs((np.round(self.pv.value, 2) - rqsvalue)) < tolerance:
            self.motor_ready = 1
        else:
            rqspv.put(rqsvalue)
            self.motor_ready = 0
        
        
def definePVs():
     pvs = {'x_center_Rqs':'9idbTAU:SM:PX:RqsPos', 'x_center_Act':'9idbTAU:SM:PX:ActPos',
            'y_center_Rqs':'9idbTAU:SY:PY:RqsPos', 'y_center_Act':'9idbTAU:SY:PY:ActPos',
            'z_value_Rqs':'9idbTAU:SM:SZ:RqsPos', 'z_value_Act':'9idbTAU:SM:SZ:ActPos',
            'tomo_rot_Rqs':'9idbTAU:SM:CT:RqsPos', 'tomo_rot_Act':'9idbTAU:SM:CT:ActPos',
            'sm_rot_Rqs':'9idbTAU:SM:ST:RqsPos', 'sm_rot_Act':'9idbTAU:SM:ST:ActPos',
            'x_width':'9idbBNP:scan1.P1WD', 'y_width':'9idbBNP:scan2.P1WD',
            'x_step':'9idbBNP:scan1.P1SI', 'y_step':'9idbBNP:scan2.P1SI',
            'dwell':'9idbBNP:scanTran3.C', 'BDA_pos':'9idbTAU:UA:UX:RqsPos',
            'det_time':'9idbBNP:3820:ElapsedReal', '1D_time':'9idbBNP:scanTran4.F',
            'xmap_stp':'9idbXMAP:StopAll', 'netCDF_stp':'9idbXMAP:netCDF1:Capture',
            'mcs_stp':'9idbBNP:3820:StopAll', 'mcs_status':'9idbBNP:3820:Acquiring',
            'xmap_status':'9idbXMAP:Acquiring', 'netCDF_save':'9idbXMAP:netCDF1:WriteFile',
            'netCDF_status':'9idbXMAP:netCDF1:WriteFile_RBV',
            'y_motor_ready':'9idbTAU:SY:Ps:Ready', 'xztp_motor_ready':'9idbTAU:SM:Ps:Ready',
            'x_piezo_val':'9idbTAU:M7009.VAL', 'y_piezo_val':'9idbTAU:M7010.VAL',
            

            'x_motorMode':'9idbTAU:SM:Ps:xMotionChoice.VAL',
            'y_motorMode':'9idbTAU:SY:Ps:yMotionChoice.VAL',
            'x_updatecenter':'9idbBNP:scan1.P1CP', 'y_updatecenter':'9idbBNP:scan2.P1CP',
            # 'x_setcenter':'9idbBNP:aoRecord11.PROC', 'y_setcenter':'9idbBNP:aoRecord12.PROC',
            'piezo_xCenter':'9idbTAU:SM:Ps:xCenter.PROC',
            'piezo_yCenter':'9idbTAU:SY:Ps:yCenter.PROC',
            'tot_lines':'9idbBNP:scan2.NPTS', 'cur_lines':'9idbBNP:scan2.CPT',
            

            'CryoCon1:In_1':'9idbCRYO:CryoCon1:In_1:Temp.VAL',
            'CryoCon1:In_3':'9idbCRYO:CryoCon1:In_3:Temp.VAL',
            'CryoCon1:In_2':'9idbCRYO:CryoCon1:In_2:Temp.VAL',
            'CryoCon3:In_2':'9idbCRYO:CryoCon3:In_2:Temp.VAL',
            'CryoCon3:Loop_2':'9idbCRYO:CryoCon3:Loop_2:SetControl.VAL',


            'run':'9idbBNP:scan2.EXSC', 'wait':'9idbBNP:scan2.WAIT', 'wait_val':'9idbBNP:scan2.WCNT',
            'pause':'9idbBNP:scan1.PAUS', 'abort':'9idbBNP:AbortScans.PROC', 
            'msg1d':'9idbBNP:scan1.SMSG',
            'fname_saveData':'9idbBNP:saveData_fileName',
            'filesys':'9idbBNP:saveData_fileSystem',
            'subdir':'9idbBNP:saveData_subDir',
            'nextsc':'9idbBNP:saveData_scanNumber',
            'basename':'9idbBNP:saveData_baseName',
            
            }
     return pvs
#    pvs = {'test1':'2idbleps:userTran2.CMTA', 'test2':'2idbleps:userTran2.CMTB', 'test3':'2idbleps:userTran2.CMTC',
#           'test4':'2idbleps:userTran2.CMTD', 'test5':'2idbleps:userTran2.CMTE', 'test6':'2idbleps:userTran2.CMTF',
#           'test7':'2idbleps:userTran2.CMTG'}


def getPVobj():
    pvObjs = {}
    pvs = definePVs()
    for k, v in pvs.items():
        pv_obj = pvObject(v, k)
        pvObjs.update({k: pv_obj})
    return pvObjs
