"""
BatchScan - Python-based user interface for microscopy beamlines at APS 
"""

import tkinter as tk
from tkinter import ttk
from setupFrame import setupFrame
from scanFrame import scanFrame

class MainWindow(tk.Frame):
    """ Start the GUI interface. """

    def __init__(self, master):
        self.master = master
        master.title("BNP Scan")
        
        self.tabControl = ttk.Notebook(master)
        setup_tab = setupFrame(self.tabControl)
        scan_tab = scanFrame(self.tabControl, setup_tab)
        setup_tab.addToScanBtn(scan_tab.insertScan)

        self.tabControl.add(setup_tab.setupfrm, text ='Scan Setup')
        self.tabControl.add(scan_tab.scanfrm, text ='Data Collection')
        self.tabControl.pack(expand=1, fill="both")
        
        
if __name__ == "__main__":
    root = tk.Tk()
    gui = MainWindow(root)
    root.geometry('1330x760')
    root.resizable(False, False)
    root.mainloop()

