'''
Control PV based on type of measurements

'''

import os, time, sys
import numpy as np
from imgProcessing import getROIcoordinate_data, getElmMap

def parmLabelToPVdict():
    d = {'width':'x_width', 'height':'y_width', 'w_step':'x_step',
         'h_step':'y_step', 'dwell':'dwell', 'x_scan':'x_center_Rqs', 
         'y_scan':'y_center_Rqs', 'z_scan': 'z_value_Rqs', 'target_theta':'sm_rot_Rqs'}
    return d

def xrfSetup(pvComm, scandic):
    d = parmLabelToPVdict()
    parms = ['width', 'height', 'w_step', 'h_step', 
             'dwell', 'y_scan', 'x_scan']
    parm_label = [d[s] for s in parms]
    parm_value = [float(scandic[s]) for s in parms]
    pvComm.writeScanInit('XRF', scandic['smpName'], str(scandic))
    pvComm.blockBeamBDA(scandic['bda'])
    pvComm.changeXYcombinedMode()
    pvComm.assignPosValToPVs(parm_label, parm_value)
    return getMotorList(scandic)

def getMotorList(scandic):
    p = ['target_theta', 'z_scan', 'y_scan', 'x_scan']
    motorlabel = ['sm_rot', 'z_value', 'y_center', 'x_center']
    mtolerance = [0.1, 0.5, 0.1, 0.1]
    mlist = []
    for p_, ml_, mt_ in zip(p, motorlabel, mtolerance):
        mlist.append((ml_, float(scandic[p_]), mt_))
    return mlist


def scanStart(pvComm, bda):
    pvComm.changeXtoPiezolMode()
    pvComm.openBeamBDA(bda)

def scanFinish(pvComm, bda):
    pvComm.blockBeamBDA(bda)
    pvComm.changeXtoCombinedMode()
    time.sleep(0.5)
    
def fileReady(coarse_sc, fdir, tlim = 30):
    fpath = os.path.join(fdir, 'img.dat/%s.h5'%(coarse_sc))
    if os.path.exists(fpath):
        fmtime = os.path.getmtime(fpath)
        tdiff = time.time() - fmtime
        if tdiff > tlim:
            return 1
        else:
            sys.stdout.write('Waiting for coarse scan file %s.h5 to be ready,'\
                     ' file modified time: %d, time difference: %d \n'\
                     %(coarse_sc, fmtime, tdiff))
            return 0
    else:
        sys.stdout.write('File %s not exisit\n'%fpath)
        return 0
    
def imgProgFolderCheck(fdir):
    img_path= os.path.join(fdir,'imgProg')
    if not os.path.exists(img_path):
        os.makedirs(img_path)
    return img_path

def getCoordinate(pvComm, coarse_sc, scandic, n_std = 2):
    fready = fileReady(coarse_sc, pvComm.userdir)
    coarse_h5path = os.path.join(pvComm.userdir, 'img.dat/%s.h5'%(coarse_sc))
    if fready:
        imgfolder = imgProgFolderCheck(pvComm.userdir)   
        imgpath = os.path.join(imgfolder, 'bbox_%s.png'%(coarse_sc))
        print(imgpath)
        elmmap = getElmMap(coarse_h5path, scandic['elm'])
        
        mask = np.ones(elmmap[0].shape)
        if scandic['use_mask']:
            maskmap = getElmMap(coarse_h5path, scandic['mask_elm'])
            mask = maskmap < (np.mean(maskmap) + n_std * np.std(maskmap.ravel()))
        m = elmmap[0] * mask
        
        x, y, w, h = getROIcoordinate_data(m, elmmap[1], elmmap[2], 
                                           n_cluster = scandic['n_clusters'],
                                           sel_cluster = scandic['sel_cluster'],
                                           figpath = imgpath)
        return np.round(x,2), np.round(y,2)
    else:
        return None
    
    
    
            




