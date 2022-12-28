"""
Created on Wed Oct 27 12:54:44 2021

@author: graceluo

Utils, misc functions
"""
import os, time, sys
import pandas as pd
sys.path.append('/home/beams11/USERBNP/scripts/roehrig/CoordinateTransforms/src')
from Transform import XZT_Transform

def coordinate_transform(angle, x, y, z):
    xzt_tform = XZT_Transform()
    xzt_tform.transform_drives(0,0,0,z,x,y,True,False)
    x_, y_, z_, t_, fx_, fy_ = xzt_tform.get_axis_positions()
    xzt_tform.transform_axes(angle, x_,y_,z_,fx_,fy_,True,False)
    c = xzt_tform.get_drive_positions()
    return {'angle':c[3], 'z':c[2], 'x':c[4], 'y':c[5]}

def getCurrentTime():
    ts = pd.Timestamp.now()
    ts_str = ts.strftime('%Y-%m-%d %X')
    return ts_str

def fileReady(next_sc, filepath, time_lim):
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
            
def imgProgFolderCheck(userdir):
        img_path= os.path.join(userdir,'imgProg')
        if not os.path.exists(img_path):
            os.makedirs(img_path)
        return img_path