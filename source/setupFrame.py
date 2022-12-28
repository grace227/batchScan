"""
Created on Tue Aug  3 11:22:02 2021

@author: graceluo

Construct setup frame for bnp_gui
"""

import tkinter as tk
from tkinter import ttk
import os, h5py, time
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib import colors, patches
from pvComm import pvComm
from misc import coordinate_transform


class setupFrame:
    def Display2Data(self, Axe, x, y):
        return Axe.transData.inverted().transform(np.array([(x, y)]))[0]

    def choose_folder(self):
        if self.pvComm.getDir() is not None:
            initialDir = os.path.join(self.pvComm.getDir(), "img.dat")
            initialDir = (
                initialDir if os.path.exists(initialDir) else self.pvComm.getDir()
            )
        else:
            initialDir = "/mnt/micdata1/2idd"

        self.h5_folder = tk.filedialog.askdirectory(initialdir=initialDir)
        self.selectfolder.set(self.h5_folder)
        ext = ".h5"
        if len(self.h5_folder) > 10:
            self.files_combobox["values"] = [
                i for i in os.listdir(self.h5_folder) if i[-len(ext) :] == ext
            ]
        else:
            self.h5_folder = tk.filedialog.askdirectory(
                initialdir="/mnt/micdata1/bnp/2021-3/"
            )

    def updateFileList(self):
        ext = ".h5"
        self.files_combobox["values"] = [
            i for i in os.listdir(self.h5_folder) if i[-len(ext) :] == ext
        ]

    def load_scan(self, *args):
        self.h5_filename = os.path.join(self.h5_folder, self.files_combobox.get())
        try:
            self.h5.close()
        except:
            pass

        try:
            self.ShowROI_Rectangle.remove()
        except (AttributeError, ValueError):
            pass

        t_diff = 10
        fmtime = os.path.getmtime(self.h5_filename)
        ctime = time.time()
        if (ctime - fmtime) >= t_diff:
            try:
                self.h5 = h5py.File(self.h5_filename, "r")
                dets = []
                i_det = max(0, self.detector_combobox.current())
                dets = (
                    self.h5["/MAPS/channel_names"][:].astype(str).tolist()
                    + self.h5["/MAPS/scaler_names"][:].astype(str).tolist()
                )
                elmScalers = np.vstack(
                    (self.h5["/MAPS/XRF_roi"][:], self.h5["/MAPS/scalers"][:])
                )
                self.detector_combobox["values"] = dets
                self.detector_combobox.current(i_det)
                self.x = self.h5["/MAPS/x_axis"][()]
                self.y = self.h5["/MAPS/y_axis"][()]
                pvlist = self.h5["/MAPS/extra_pvs"][0].astype(str).tolist()
                pvval = self.h5["/MAPS/extra_pvs"][1].astype(str).tolist()
                if len(pvlist) < 5:
                    self.file_z = None
                    self.file_theta = None
                
                else:
                    self.file_z = float(
                        pvval[pvlist.index(self.pvComm.pvs["z_value_Act"].pv.pvname)]
                    )
                    self.file_theta = float(
                        pvval[pvlist.index(self.pvComm.pvs["sm_rot_Act"].pv.pvname)]
                    )
                
                self.Image2D = self.Axe2D.imshow(
                    elmScalers[i_det],
                    aspect="equal",
                    interpolation="nearest",
                    cmap="inferno",
                    origin="lower",
                    #                                                 extend = (np.min(self.x),np.max(self.x), np.min(self.y), np.max(self.y)),
                    norm=colors.SymLogNorm(linthresh=0.5)
                    if self.log_button.config("relief")[-1] == "sunken"
                    else colors.Normalize(),
                )
                self.Canvas2D.draw()
                if self.file_z is None:
                    self.openfilemsg.set("Samz PV not found %s" % self.h5_filename)
                    self.open_msg_label.config(fg="red")
                else:
                    self.openfilemsg.set("%s is open" % self.h5_filename)
                    self.open_msg_label.config(fg="green")
            except:
                self.openfilemsg.set("Having trouble opening %s" % self.h5_filename)
                self.open_msg_label.config(fg="red")
        else:
            self.openfilemsg.set("File not ready, getting update from other process")
            self.open_msg_label.config(fg="red")

    def plot_data(self, *args):
        i_det = self.detector_combobox.current()
        elmScalers = np.vstack(
            (self.h5["/MAPS/XRF_roi"][:], self.h5["/MAPS/scalers"][:])
        )
        self.Image2D.set_array(np.array(elmScalers[i_det]))
        if self.log_button.config("relief")[-1] == "sunken":
            # self.Image2D.set_norm(colors.LogNorm())
            self.Image2D.set_norm(colors.SymLogNorm(linthresh=0.5))
        else:
            self.Image2D.set_norm(colors.Normalize())
        self.Canvas2D.draw()

    def logscale_changed(self):
        if self.log_button.config("relief")[-1] == "sunken":
            self.log_button.config(relief="raised")
            self.Image2D.set_norm(colors.Normalize())
        else:
            self.log_button.config(relief="sunken")
            self.Image2D.set_norm(colors.SymLogNorm(linthresh=0.5))
        self.Canvas2D.draw()

    def Draw_Rectangle(self, xmin, xmax, ymin, ymax, color, lw=2, animated=False):
        Rectangle = patches.Rectangle(
            (xmin, ymin),
            width=xmax - xmin,
            height=ymax - ymin,
            alpha=1,
            edgecolor="w",
            fill=False,
            linewidth=lw,
            animated=animated,
        )
        self.Axe2D.add_patch(Rectangle)
        return Rectangle


    def Canvas2D_Button_Pressed(self, event):
        self.xstart, self.ystart = list(
            map(
                lambda x: int(round(x, 0)),
                (self.Display2Data(self.Axe2D, event.x, event.y)),
            )
        )
        if event.button == 1:
            self.xycorr.set(
                "x, y: (%.2f, %.2f)" % (self.x[self.xstart], self.y[self.ystart])
            )
        if (event.button == 1) & (self.insertType.get() == "XY Center"):
            try:
                self.ShowROI_Rectangle.remove()
            except (AttributeError, ValueError):
                pass
            self.updateXYcenter()
        elif (event.button == 3) & (self.insertType.get() == "ScanBox"):
            self.Rectangle_Drawing = True
            try:
                self.ShowROI_Rectangle.remove()
            except (AttributeError, ValueError):
                pass
            self.Canvas2D.mpl_disconnect(self.Canvas2D_Button_Press_Event)
            self.Canvas2D_Button_Release_Event = self.Canvas2D.mpl_connect(
                "button_release_event", self.Canvas2D_Button_Released
            )

    def Canvas2D_Button_Released(self, event):
        self.xend, self.yend = list(
            map(
                lambda x: int(round(x, 0)),
                (self.Display2Data(self.Axe2D, event.x, event.y)),
            )
        )

        self.Canvas2D.mpl_disconnect(self.Canvas2D_Button_Release_Event)
        self.Canvas2D_Button_Press_Event = self.Canvas2D.mpl_connect(
            "button_press_event", self.Canvas2D_Button_Pressed
        )

        if self.Rectangle_Drawing:
            self.Rectangle_Drawing = False
            self.non_animated_background = None
            try:
                self.ShowROI_Rectangle.remove()
            except (AttributeError, ValueError):
                pass
            xmin = int(min(self.xend, self.xstart))
            xmax = int(max(self.xend, self.xstart))
            ymin = int(min(self.yend, self.ystart))
            ymax = int(max(self.yend, self.ystart))
            self.ShowROI_Rectangle = self.Draw_Rectangle(xmin, xmax, ymin, ymax, "w")
            self.updateScanBoxParms()

    def Canvas2D_Mouser_Hover(self, event):
        self.xend, self.yend = list(
            map(
                lambda x: int(round(x, 0)),
                (self.Display2Data(self.Axe2D, event.x, event.y)),
            )
        )
        try:
            dim_y, dim_x = self.Image2D.get_array().shape
        except:
            return
        if (
            (self.yend < dim_y - 0.5)
            and (self.yend > -0.5)
            and (self.xend > -0.5)
            and (self.xend < dim_x - 0.5)
        ):
            if self.Rectangle_Drawing:
                if self.non_animated_background != None:
                    # restore the clean slate background
                    self.Canvas2D.restore_region(self.non_animated_background)
                    if self.xstart > self.xend:  # modify the starting point
                        self.Rectangle.set_x(self.xend)
                    self.Rectangle.set_width(abs(self.xend - self.xstart))
                    if self.ystart > self.yend:  # modify the starting point
                        self.Rectangle.set_y(self.yend)
                    self.Rectangle.set_height(abs(self.yend - self.ystart))
                    self.Axe2D.draw_artist(self.Rectangle)
                    self.Canvas2D.blit(self.Axe2D.bbox)
                else:
                    xmax = int(max(self.xend, self.xstart))
                    xmin = int(min(self.xend, self.xstart))
                    ymax = int(max(self.yend, self.ystart))
                    ymin = int(min(self.yend, self.ystart))
                    self.Rectangle = self.Draw_Rectangle(
                        xmin, xmax, ymin, ymax, "w", animated=True
                    )
                    self.Canvas2D.draw()
                    self.non_animated_background = self.Canvas2D.copy_from_bbox(
                        self.Axe2D.bbox
                    )

    def updateXYcenter(self):
        x_scan = np.round(self.x[self.xstart], 2)
        y_scan = np.round(self.y[self.ystart], 2)
        z_scan = np.round(self.file_z, 2)
        target_theta = self.file_theta

        slabel = ["x_scan", "y_scan", "z_scan", "target_theta"]
        for s in slabel:
            self.scanParms[s].delete(0, tk.END)
            self.scanParms[s].insert(0, "%.2f" % (eval(s)))

        slabel = ["x_theta0", "y_theta0", "z_theta0"]
        if (self.file_theta ** 2) < 1e-3:
            svlabel = ["x_scan", "y_scan", "z_scan"]
        else:
            e = ""
            svlabel = ["e"] * 3

        for s_, sv_ in zip(slabel, svlabel):
            self.scanParms[s_].delete(0, tk.END)
            self.scanParms[s_].insert(0, "%s" % (str(eval(sv_))))

    def updateScanBoxParms(self):
        x_scan = np.round((self.x[self.xstart] + self.x[self.xend]) / 2, 2)
        y_scan = np.round((self.y[self.ystart] + self.y[self.yend]) / 2, 2)
        width = abs(self.x[self.xstart] - self.x[self.xend])
        height = abs(self.y[self.ystart] - self.y[self.yend])
        if self.file_z is not None:    
            z_scan = np.round(self.file_z, 2)
            target_theta = self.file_theta
            slabel = ["x_scan", "y_scan", "width", "height", "z_scan", "target_theta"]
            for s in slabel:
                self.scanParms[s].delete(0, tk.END)
                self.scanParms[s].insert(0, "%.2f" % (eval(s)))
    
            slabel = ["x_theta0", "y_theta0", "z_theta0"]
            if (self.file_theta ** 2) < 1e-3:
                svlabel = ["x_scan", "y_scan", "z_scan"]
            else:
                e = ""
                svlabel = ["e"] * 3
    
            for s_, sv_ in zip(slabel, svlabel):
                self.scanParms[s_].delete(0, tk.END)
                self.scanParms[s_].insert(0, "%s" % (str(eval(sv_))))
        else:
            slabel = ["x_scan", "y_scan", "width", "height"]
            for s in slabel:
                self.scanParms[s].delete(0, tk.END)
                self.scanParms[s].insert(0, "%.2f" % (eval(s)))
            flabel = ['z_scan', 'target_theta', 'x_theta0', 'y_theta0', 'z_theta0']
            for f in flabel: 
                self.scanParms[f].delete(0, tk.END)

    def checkEntryDigit(self, P):
        if (P == "") | (P == "-"):
            return True
        try:
            float(P)
            return True
        except:
            return False

    def calcTime(self):
        strlist = ["width", "height", "w_step", "h_step", "dwell"]
        try:
            value = [float(self.scanParms[s].get()) for s in strlist]
        except:
            value = [0] * len(strlist)

        if value[0] > 80:
            self.calctime.set("Width can not be bigger than 80")
            self.calctime_out.config(fg="red")
        elif 0 not in value:
            eta_ms = value[-1] * value[0] * value[1] / value[2] / value[3]
            eta_min = eta_ms / 1e3 / 60 / 0.8
            self.calctime.set("%.3f" % (eta_min))
            self.calctime_out.config(fg="green")


    def getUserDir(self):
        self.pardir.set(self.pvComm.getDir())

    def addToScanBtn(self, func):
        add_scan_btn = tk.Button(
            self.setupfrm, text="Add to scan list", command=func, width=50
        )
        add_scan_btn.grid(row=self.row + 5, column=self.col, columnspan=4)

    def updatexyz0(self):
        if (self.pvComm.getSMAngle() ** 2) < 1e-3:
            self.fillxyz0(empty=False)
            self.coordtform()
            self.updatexyz_msg.set(
                "x-, y-, z- theta0 updated"
                + "\n"
                + "Coordinate transformed. x-, y-, z- scan values updated"
            )
            self.updatexyz_label.config(fg="green")
        else:
            self.updatexyz_msg.set("Theta (Rotation) motor is not at 0")
            self.updatexyz_label.config(fg="red")
            
    def fillxyz0(self, empty = True):
        if empty:
            x,y,z = ['','','']
        else:
            x, y, z = self.pvComm.getXYZcenter()
        for a_, v_ in zip(["x_theta0", "y_theta0", "z_theta0"], [x, y, z]):
            self.scanParms[a_].delete(0, tk.END)
            self.scanParms[a_].insert(0, str(v_)) 
            
    def fillxyzScan(self, empty = True):
        if empty:
            x,y,z,theta = ['','','', '']
        else:
            x, y, z = self.pvComm.getXYZcenter()
            theta = self.pvComm.getSMAngle()
        for a_, v_ in zip(['x_scan', 'y_scan', 'z_scan', 'target_theta'], [x, y, z, theta]):
            self.scanParms[a_].delete(0, tk.END)
            self.scanParms[a_].insert(0, str(v_)) 
    
    def updatexyz(self):
        if (self.pvComm.getSMAngle() ** 2) < 1e-3:
            self.fillxyz0(empty=False)
            self.fillxyzScan()
        else:
            self.fillxyz0()
            self.fillxyzScan(empty=False)


    def coordtform(self):
        fields = ["target_theta", "x_theta0", "y_theta0", "z_theta0"]
        fvals = [float(self.scanParms[a_].get()) for a_ in fields]
        ctform = coordinate_transform(*fvals)
        writeFields = ["x_scan", "y_scan", "z_scan"]
        wfv = [round(ctform[a], 2) for a in ["x", "y", "z"]]
        for a_, v_ in zip(writeFields, wfv):
            self.scanParms[a_].delete(0, tk.END)
            self.scanParms[a_].insert(0, str(v_))
        self.updatexyz_msg.set("Coordinate transformed. x-, y-, z- scan values updated")
        self.updatexyz_label.config(fg="green")

    def __init__(self, tabControl):
        self.setupfrm = ttk.Frame(tabControl)

        self.selectfolder = tk.StringVar()
        self.selectfolder.set(" ")
        mdafolder_button = tk.Button(
            self.setupfrm, text="Open Folder", command=self.choose_folder
        )
        mdafolder_button.grid(column=0, row=0, padx=(5, 5), pady=(5, 5))
        folder_txt = tk.Label(self.setupfrm, textvariable=self.selectfolder)
        folder_txt.grid(row=0, column=1, columnspan=3)

        scannum_txt = tk.Label(self.setupfrm, text="Files:")
        scannum_txt.grid(column=0, row=1, pady=(5, 5), padx=(5, 5))

        self.scfile_sv = tk.StringVar()
        self.files_combobox = ttk.Combobox(
            self.setupfrm, textvariable=self.scfile_sv, state="readonly", width=22
        )
        self.files_combobox.grid(column=1, row=1, padx=(5, 5), pady=(5, 5))
        self.files_combobox.bind("<<ComboboxSelected>>", self.load_scan)
        self.pvComm = pvComm()
        #        self.scannum_entry = tk.Entry(self.setupfrm, width=10)
        #        self.scannum_entry.grid(column=1, row = 1, padx=(5,5), pady=(5,5))

        loadscan_button = tk.Button(
            self.setupfrm, text="Update", command=self.updateFileList
        )
        loadscan_button.grid(column=2, row=1, padx=(5, 5), pady=(5, 5))
        detector_sv = tk.StringVar()
        self.detector_combobox = ttk.Combobox(
            self.setupfrm, textvariable=detector_sv, state="readonly", width=20
        )
        self.detector_combobox.grid(column=3, row=1, padx=(5, 5), pady=(5, 5))
        self.detector_combobox.bind("<<ComboboxSelected>>", self.plot_data)

        self.log_button = tk.Button(
            self.setupfrm, text="Log", command=self.logscale_changed
        )
        self.log_button.grid(column=0, row=52, padx=(5, 5), pady=(0, 0))
        self.xycorr = tk.StringVar()
        self.xycorr.set("x, y: (0.00, 0.00)")
        xycorr_label = tk.Label(self.setupfrm, textvariable=self.xycorr)
        xycorr_label.grid(row=52, column=1)

        self.openfilemsg = tk.StringVar()
        self.openfilemsg.set("")
        self.open_msg_label = tk.Label(self.setupfrm, textvariable=self.openfilemsg)
        self.open_msg_label.grid(row=53, column=0, columnspan=2)
        self.file_theta = 0
        self.file_z = 0

        self.Figure2D = Figure()
        self.Axe2D = self.Figure2D.add_axes([0, 0, 1, 1])
        self.Axe2D.set_axis_off()

        self.Canvas2D = FigureCanvasTkAgg(self.Figure2D, master=self.setupfrm)
        self.Canvas2D.draw()
        self.Canvas2D.get_tk_widget().config(width=600, height=600, cursor="cross")
        self.Canvas2D.get_tk_widget().grid(
            column=0,
            columnspan=10,
            row=2,
            rowspan=50,
            padx=(10, 5),
            pady=(5, 5),
            sticky="W",
        )

        self.Canvas2D_Mouse_Hover_Event = self.Canvas2D.mpl_connect(
            "motion_notify_event", self.Canvas2D_Mouser_Hover
        )
        self.Canvas2D_Button_Press_Event = self.Canvas2D.mpl_connect(
            "button_press_event", self.Canvas2D_Button_Pressed
        )
        self.Rectangle_Drawing = False
        self.Dot_Drawing = False
        self.non_animated_background = None

        self.row = 2
        self.col = 10
        self.scantype_txt = tk.Label(
            self.setupfrm, text="1. Choose a type of scan below:"
        )
        self.scantype_txt.grid(
            row=self.row, column=self.col, padx=(0, 400), columnspan=10
        )

        self.scanType = tk.StringVar(self.setupfrm)
        self.scanType.set("XRF")
        scantype = ["XRF",'Coarse-Fine (Fixed Angle)', "Angle Sweep", "Coarse-Fine"]
        padx = [(18, 10), (0, 10), (0, 10), (0, 10)]
        self.row += 1
        for i, s in enumerate(scantype):
            a = ttk.Radiobutton(
                master=self.setupfrm, text=s, variable=self.scanType, value=s,
            )
            a.grid(row=self.row, column=self.col + i, padx=padx[i], stick='w')

        self.row += 1
        self.inserttype_txt = tk.Label(
            self.setupfrm, text="2. Choose a method to insert scan parameters:"
        )
        self.inserttype_txt.grid(
            row=self.row, column=self.col, padx=(0, 320), columnspan=8
        )
        self.insertType = tk.StringVar(self.setupfrm)
        self.insertType.set("Manual")
        inserttype = ["Manual", "XY Center", "ScanBox"]
        padx = [(0, 84), (0, 120), (0, 120)]
        self.row += 1
        for i, s in enumerate(inserttype):
            a = ttk.Radiobutton(
                master=self.setupfrm, text=s, variable=self.insertType, value=s
            )
            a.grid(row=self.row, column=self.col + i, padx=padx[i])

        self.scanParms = {}
        self.row += 2
        self.col = 10
        ncol = 3
        self.inputs_labels = [
            [
                "x_theta0",
                "y_theta0",
                "z_theta0",
                "x_scan",
                "y_scan",
                "z_scan",
                "dwell",
                "width",
                "w_step",
                "target_theta",
                "height",
                "h_step",
            ],
            [
                "theta_min",
                "theta_max",
                "theta_inc",
                "elm",
                "width_fine",
                "w_step_fine",
                "n_clusters",
                "height_fine",
                "h_step_fine",
                "sel_cluster",
                "dwell_fine",
                "use_mask",
                "mask_elm",
            ],
        ]
        #        corr = self.pvComm.getXYZcenter()
        temp_input = [0] * 6 + [20, 20, 1, 15, 10, 1]
        vcmd = self.setupfrm.register(self.checkEntryDigit)
        for i, s in enumerate(self.inputs_labels[0]):
            if i % ncol == 0:
                self.row += 1
            sv = tk.StringVar()
            sv.trace("w", lambda name, index, mode, sv=sv: self.calcTime())
            tk.Label(self.setupfrm, text=s + ":").grid(
                row=self.row, column=self.col + i % ncol, sticky="W", columnspan=2
            )
            a = tk.Entry(
                self.setupfrm,
                width=10,
                textvariable=sv,
                validate="all",
                validatecommand=(vcmd, "%P"),
            )
            a.grid(row=self.row, column=self.col + i % ncol, padx=(70, 0))
            a.insert(0, str(temp_input[i]))
            #            a.insert(0,'0')
            self.scanParms.update({s: a})

        self.row += 1
        smp_txt = tk.Label(self.setupfrm, text="Sample name:")
        smp_txt.grid(row=self.row, column=self.col, sticky="w")
        self.smp_name = tk.StringVar()
        smp_entry = tk.Entry(self.setupfrm, textvariable=self.smp_name)
        smp_entry.grid(
            row=self.row, column=self.col, columnspan=2, sticky="w", padx=(88, 0)
        )

        bda_txt = tk.Label(self.setupfrm, text="BDA Position:")
        bda_txt.grid(row=self.row, column=self.col + 1, sticky="w", padx=(100, 0))
        self.bda = tk.StringVar()
        bda_entry = tk.Entry(
            self.setupfrm,
            textvariable=self.bda,
            validate="all",
            validatecommand=(vcmd, "%P"),
        )

        # TO DO: get bda position from save state instead from motor
        self.bda.set("%.2f" % (self.pvComm.getBDAx()))
        bda_entry.grid(
            row=self.row, column=self.col + 2, sticky="w", padx=(25, 0), columnspan=2
        )

        self.row += 1
        updatexyz0_btn = tk.Button(
            self.setupfrm, text="XYZ_0 + transform", command=self.updatexyz0
        )
        updatexyz0_btn.grid(row=self.row, column=self.col, columnspan=2)
        updatexyz_btn = tk.Button(
            self.setupfrm, text="XYZ from PV", command=self.updatexyz
        )
        updatexyz_btn.grid(row=self.row, column=self.col + 1, columnspan=2)

        self.row += 1
        calctime_txt = tk.Label(self.setupfrm, text="Estimated scan time (min):")
        calctime_txt.grid(row=self.row, column=self.col, sticky="w")
        self.calctime = tk.StringVar()
        self.calctime.set("0")
        self.calctime_out = tk.Label(
            self.setupfrm, width=10, textvariable=self.calctime
        )
        self.calctime_out.grid(row=self.row, column=self.col + 1, sticky="w")

        self.row += 1
        self.updatexyz_msg = tk.StringVar()
        self.updatexyz_msg.set("")
        self.updatexyz_label = tk.Label(self.setupfrm, textvariable=self.updatexyz_msg)
        self.updatexyz_label.grid(
            row=self.row, column=self.col, sticky="w", columnspan=3
        )

        self.row += 4
        self.inserttype_txt = tk.Label(
            self.setupfrm, text="Additional scan parameters for tomography"
        )
        self.inserttype_txt.grid(
            row=self.row, column=self.col, padx=(0, 0), columnspan=8
        )
        for i, s in enumerate(self.inputs_labels[1]):
            if i % ncol == 0:
                self.row += 1
            tk.Label(self.setupfrm, text=s + ":").grid(
                row=self.row, column=self.col + i % ncol, sticky="W", columnspan=2
            )
            if (s == "elm") | (s == "mask_elm"):
                a = tk.Entry(self.setupfrm, width=10)
                a.insert(0, "P")
            else:
                a = tk.Entry(
                    self.setupfrm,
                    width=10,
                    validate="all",
                    validatecommand=(vcmd, "%P"),
                )
                a.insert(0, "0")
            a.grid(row=self.row, column=self.col + i % ncol, padx=(70, 0))
            self.scanParms.update({s: a})

        row = self.row + 7
        self.pardir = tk.StringVar()
        self.pardir.set(self.pvComm.getDir())
        scdir_txt = tk.Button(
            self.setupfrm, text="Current data save directory:", command=self.getUserDir
        )
        scdir_txt.grid(row=row, column=self.col, sticky="w")
        pardir_out = tk.Label(self.setupfrm, textvariable=self.pardir)
        pardir_out.grid(row=row, column=self.col + 1, sticky="w", columnspan=3)

        row += 2
        tot_est_txt = tk.Label(self.setupfrm, text="Estimated total scan time:")
        tot_est_txt.grid(row=row, column=self.col, sticky="w")
        self.tot_time = tk.StringVar()
        self.tot_time.set("0")
        tot_est_val = tk.Label(self.setupfrm, textvariable=self.tot_time)
        tot_est_val.grid(row=row, column=self.col + 1, sticky="w")
