"""
Created on Wed Oct 27 12:54:44 2021

@author: graceluo

Functions / Classes associated with logging
"""

import sys

class stdoutRedirect(object):
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self,string):
        self.text_space.insert('end', string)
        self.text_space.see('end')
    
    def flush(self):
        pass
    
def stdoutToTextbox(textbox):
    sys.stdout = stdoutRedirect(textbox)
    
class logger(object):
    def __init__(self, fpath, logtxtOnly = True):
        self.fpath = fpath
        self.fid = None
        self.logtxtOnly = logtxtOnly        
        
    def openFile(self):
        if self.fid is None:
            self.fid = open(self.fpath, 'a')
        elif self.fid.closed:
            self.fid = open(self.fpath, 'a')
        
    def write(self, msg, logtxtOnly = None):
        if logtxtOnly is None:
            logtxtOnly = self.logtxtOnly
        
        if (not logtxtOnly) | (self.fpath is None):
            sys.stdout.write(msg)
            sys.stdout.flush()
        if (self.fpath is not None):
            sys.stdout.write(msg)
            sys.stdout.flush()
            self.openFile()
            self.fid.write(msg)
            self.fid.flush()
