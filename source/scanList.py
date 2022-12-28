#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 31 07:04:22 2021

@author: graceluo

Create a scanlist class 
"""
import tkinter as tk
from tkinter import ttk
import numpy as np
from misc import coordinate_transform
import pandas as pd

class scanList(object):
    
    def __init__(self, scanfrm, inputs_labels, calctime_out,
                 scanType, smp_name, bda, tot_time, scanParms):
        self.scanfrm = scanfrm
        self.inputs_labels = inputs_labels
        self.sclist = None
        self.sclist_col = None
        self.sclistConfig()
        self.calctime_out = calctime_out
        self.scanType = scanType
        self.smp_name = smp_name
        self.bda = bda
        self.tot_time = tot_time
        self.scanParms = scanParms
        self.scanidx = 0
        
        self.pbarlistmsg = tk.StringVar()
        self.pbarlistmsg.set('Batch scan progress:')
        pbar_sclist_txt = tk.Label(self.scanfrm, textvariable = self.pbarlistmsg)
        pbar_sclist_txt.grid(row = 23, column = 1, sticky='w', pady = (35, 0),
                             padx = (20,0))
        self.pbarlistval = tk.DoubleVar()
        self.pbarlistval.set(0.0)
        self.pbar_sclist = ttk.Progressbar(self.scanfrm, orient = tk.HORIZONTAL, 
                                           length = 300, mode = 'determinate',
                                           variable = self.pbarlistval)
        self.pbar_sclist.grid(row = 23, column = 1, columnspan = 3, sticky='w', 
                              pady = (35,0), padx=(180,0))
        
    def sclistConfig(self):
        self.sclist = ttk.Treeview(self.scanfrm, height='20')
        t_col = self.inputs_labels[1].copy()
        
        # the following fields are not carried over to scanlist table
        [t_col.remove(i) for i in ['theta_min', 'theta_max', 'theta_inc',
         'width_fine', 'w_step_fine', 'height_fine', 'h_step_fine', 'dwell_fine']]
        
        inlabels = self.inputs_labels[0]
        inlabels.insert(0, inlabels.pop(inlabels.index('target_theta')))
        t_col_mod = ['id', 'status', 'scanType', 'smpName'] + inlabels + t_col + ['eta']
        
        self.sclist_col = tuple(t_col_mod)
        self.sclist['columns']= self.sclist_col
        self.sclist.column('#0', width=0, stretch=tk.NO)
                           
        for c in self.sclist_col:
            if (c == 'id') | (c == 'smpName'):
                self.sclist.column(c, anchor = tk.CENTER, width=75, stretch=tk.NO)
            else:
                self.sclist.column(c, anchor = tk.CENTER, width=57, minwidth=70, stretch=tk.YES)
            self.sclist.heading(c, text = c, anchor = tk.CENTER)
        self.sclist.grid(row = 0, column = 0, columnspan = 12, padx=(5,0),
                         stick = 'w')
        
        sb = tk.Scrollbar(self.scanfrm, orient=tk.VERTICAL,command=self.sclist.yview)
        sb.place(x=1285, y=18, height=400)
        sb_h = tk.Scrollbar(self.scanfrm, orient=tk.HORIZONTAL, command=self.sclist.xview)
        sb_h.place(x=5, y=420, width=1276, height = 12)
        self.sclist.config(yscrollcommand=sb.set, xscrollcommand = sb_h.set)
        self.sclist.bind("<Double-1>", self.scanListEdit)
        self.sclist.bind('<1>', self.closePopUpEntry)
        
        
    def insertScan(self):
        sctime = float(self.calctime_out['text'])
        if (sctime > 0.0) & (self.scanParms['target_theta'].get() != ''):
            if self.scanType.get() == 'XRF':
                scprm_theta0 = [len(self.scanParms[i+'_theta0'].get()) for i in ['x', 'y', 'z']]
                if not all(scprm_theta0):
                    self.insertParmEntry()
                else:
                    self.insertParmEntry(theta=float(self.scanParms['target_theta'].get()))
            elif self.scanType.get() == 'Coarse-Fine (Fixed Angle)':
                self.insertParmEntry()
            else:
                t_min = float(self.scanParms['theta_min'].get())
                t_inc = float(self.scanParms['theta_inc'].get())
                t_max = float(self.scanParms['theta_max'].get()) + t_inc
                angles = np.arange(t_min, t_max, t_inc)
                
                for a in angles:
                    self.insertParmEntry(theta=a)
                    
            self.tot_time.set('%.3f'%(self.getTotalTime()))
            eta_dt = pd.Timestamp.now() +pd.DateOffset(minutes = self.getTotalTime())
            self.tot_time.set('%s'%(eta_dt.strftime('%Y-%m-%d %X')))
        else:
            print('Scan not added, scan parameters invalid')     
   
    def insertParmEntry(self, theta = None):
        t_col = self.inputs_labels[1].copy()
        [t_col.remove(i) for i in ['theta_min', 'theta_max', 'theta_inc']]
        scanparm_label = self.inputs_labels[0] + t_col
        
        scanparm = {k:self.scanParms[k].get() for k in scanparm_label}
        scanparm.update({'id':self.scanidx, 'status':'queue', 
                         'scanType':self.scanType.get(), 
                         'smpName':self.smp_name.get(),
                         'eta':float(self.calctime_out['text'])})
                    
        if theta is not None:
            if self.scanType.get() == 'Coarse-Fine': sctype = ['Coarse', 'Fine']
            else: sctype = [self.scanType.get()]
            
            try:
                clabel = ['x', 'y', 'z']
                c0 = [theta] + [float(scanparm[s+'_theta0']) for s in clabel]
                ctform = coordinate_transform(*c0)
                for c in clabel:
                    scanparm[c+'_scan'] = '%.2f'%ctform[c]
                
                for i in sctype:  
                    if i == 'Fine':
    #                    copy fine(w, h, steps) to regular w, h, steps
                        dlabels = ['width', 'height', 'w_step', 'h_step', 'dwell']
                        slabels = ['width_fine', 'height_fine', 'w_step_fine', 'h_step_fine', 'dwell_fine'] 
                        
                        for d_, s_ in zip(dlabels, slabels):
                            scanparm[d_] = scanparm[s_]
                        
                        for s in ['x_scan', 'y_scan']:
                            scanparm[s] = ''
                            
                    scanparm['target_theta'] = theta
                    scanparm['scanType'] = i
                    sparm = [scanparm[s_] for s_ in list(self.sclist_col)]
                    self.sclist.insert(parent='', index=self.scanidx, iid=self.scanidx,
                                       text='', values=tuple(sparm))
                    self.scanidx += 1
            except:
                print('Scan not added, no xyz (theta0) found')   
        elif self.scanType.get() == 'Coarse-Fine (Fixed Angle)':
            sctype = ['Coarse', 'Fine']
            for i in sctype:  
                if i == 'Fine':
                    dlabels = ['width', 'height', 'w_step', 'h_step', 'dwell']
                    slabels = ['width_fine', 'height_fine', 'w_step_fine', 'h_step_fine', 'dwell_fine'] 
                    
                    for d_, s_ in zip(dlabels, slabels):
                        scanparm[d_] = scanparm[s_]
                    
                    for s in ['x_scan', 'y_scan']:
                        scanparm[s] = ''
                        
                # scanparm['target_theta'] = theta
                scanparm['scanType'] = i
                sparm = [scanparm[s_] for s_ in list(self.sclist_col)]
                self.sclist.insert(parent='', index=self.scanidx, iid=self.scanidx,
                                   text='', values=tuple(sparm))
                self.scanidx += 1
            
        else:
            sparm = [scanparm[s_] for s_ in list(self.sclist_col)]
            self.sclist.insert(parent='', index=self.scanidx, iid=self.scanidx,
                                   text='', values=tuple(sparm))
            self.scanidx += 1
        self.pbarInit()
    
    def scanListEdit(self, event):
        ''' Executed, when a row is double-clicked. Opens 
        read-only EntryPopup above the item's column, so it is possible
        to select text '''

        rowid = self.sclist.identify_row(event.y)
        column = self.sclist.identify_column(event.x)
        columnid = int(column[1:])-1
        values = self.sclist.item(rowid, 'values')
        xpad = 35
        ypad = 10
        
        if len(values) > 0:
            if (columnid > 2) & (values[1] == 'queue'):
                # get column position info
                x,y,width,height = self.sclist.bbox(rowid, column)
                # place Entry popup properly         
                self.sclist.entryPopup = EntryPopup(self.sclist, rowid, columnid, values)
                self.sclist.entryPopup.place(x=x+xpad, y=y+ypad, width = width, height=height, anchor='center')
            elif values[1] != 'queue':
                print('Not editable when the selected scan is running or done\n')
            else:
                print('ID, Status and ScanType are not editable\n')
            
    def closePopUpEntry(self, event):
        try:
            self.sclist.entryPopup.destroy()
        except AttributeError:
            pass
    
    def getTotalTime(self, remaining_st = 0):
        t = remaining_st / 60
        for record in self.sclist.get_children():
            if self.sclist.item(record)['values'][1] == 'queue':
                t += float(self.sclist.item(record)['values'][-1])
        return t
    
    
    def clearSclist(self):
        for record in self.sclist.get_children():
            self.sclist.delete(record)
        self.pbarInit()
            
    def removeSelect(self):
        for record in self.sclist.selection():
            self.sclist.delete(record)
        self.pbarInit()
        
    def getNumQueue(self):
        n = 0
        for record in self.sclist.get_children():
            s = self.sclist.item(record)['values'][1]
            if s != 'aborted':
                n += 1
        return n
    
    def getNumDone(self):
        n = 0
        for record in self.sclist.get_children():
            s = self.sclist.item(record)['values'][1]
            if (s == 'done') | (s == 'scanning'):
                n += 1
        return n
   
    def searchQueue(self):
        self.parm = {}
        values = []
        for record in self.sclist.get_children():
            if self.sclist.item(record)['values'][1] == 'queue':
                self.parm = {n:v for n, v in zip(self.sclist_col, self.sclist.item(record)['values'])}
                values = [v for v in self.sclist.item(record)['values']]
                values[1] = 'scanning'
                return record, values
        return None, []
    
    def pbarInit(self):
        self.pbarlistmsg.set('Batch scan progress (%d/%d):'%(self.getNumDone(), self.getNumQueue()))
        self.pbarlistval.set(0.0)
        if self.getNumQueue() == 0:
            self.pbarlistval.set(0)
        else:
            self.pbarlistval.set(self.getNumDone() / self.getNumQueue() * 100)
            
class EntryPopup(ttk.Entry):
    
    def __init__(self, parent, iid, column, values, **kw):
        ''' If relwidth is set, then width is ignored '''
        super().__init__(parent, **kw)
        self.sclist = parent
        self.iid = iid
        self.column = column
        self.values = values

        self.insert(0, values[column]) 
        self['exportselection'] = False

        self.focus_force()
        self.bind("<Return>", self.on_return)
        self.bind("<Escape>", lambda *ignore: self.destroy())

    def on_return(self, event):
        uvalues = [s for s in self.values]
        uvalues[self.column] = self.get()
        self.sclist.item(self.iid, text='', values=tuple(uvalues))
        self.destroy()

