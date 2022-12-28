import numpy as np
import h5py, os
from sklearn.cluster import KMeans
from skimage.measure import regionprops
from skimage.draw import rectangle, polygon_perimeter
from skimage.transform import resize 
from scipy.fftpack import fft2, ifft2
import skimage.filters
import matplotlib.patches as mpatches
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def estShifts(refSc, currSc, fpath, elm):
    ref, ref_x_pos, ref_y_pos = getElmMap(os.path.join(fpath, refSc), elm)
    mov, mov_x_pos, mov_y_pos = getElmMap(os.path.join(fpath, currSc), elm)
    ref_resize = resize(ref, mov.shape)
    s1, s2 = phaseCorrelate(ref_resize, mov)
    fig = plt.figure()
    plt.imshow(ref_resize, cmap='Greens', alpha = 0.5)
    plt.imshow(np.roll(mov.copy(), (int(s1), int(s2))), cmap='Reds', alpha = 0.5)
    ss_x = np.diff(mov_x_pos)[0]*s1
    ss_y = np.diff(mov_y_pos)[0]*s2
    plt.title('x_shift_um:%.2f, y_shift_um:%.2f, x_shift_pixel:%d, y_shift_pixel:%d'%(ss_x, ss_y, s1, s2))
    return ss_x, ss_y, fig

def getROIcoordinate(fname, elm, savefig = True, figpath = None, n_cluster = 2, sel_cluster = 1):
    elmmap, x_pos, y_pos = getElmMap(fname, elm)
    kmeanMap = kmean_analysis(n_cluster,elmmap, 42, plotoption = True)
    region_prop = regionprops(np.array(kmeanMap[0]==sel_cluster, dtype='int'))
    region_bbox = region_prop[0].bbox
    fig = plotBBox(elmmap, region_bbox, x_pos, y_pos)
        
    width = x_pos[region_bbox[3]-1]- x_pos[region_bbox[1]]
    height = y_pos[region_bbox[2]-1]- y_pos[region_bbox[0]]
    
    new_x = (x_pos[region_bbox[3]-1]- x_pos[region_bbox[1]])/2 + x_pos[region_bbox[1]]
    new_y = (y_pos[region_bbox[2]-1]- y_pos[region_bbox[0]])/2 + y_pos[region_bbox[0]]
    
    if savefig:
        fig.savefig(figpath, dpi=100, transparent=True)
        
    return new_x, new_y, width, height

def getROIcoordinate_data(elmmap, x_pos, y_pos, savefig = True, figpath = None, n_cluster = 2, sel_cluster = 1):
    kmeanMap = kmean_analysis(n_cluster,elmmap, 42, plotoption = False)
    region_prop = regionprops(np.array(kmeanMap[0]==sel_cluster, dtype='int'))
    region_bbox = region_prop[0].bbox
    fig = plotBBox(elmmap, region_bbox, x_pos, y_pos)
        
    width = x_pos[region_bbox[3]-1]- x_pos[region_bbox[1]]
    height = y_pos[region_bbox[2]-1]- y_pos[region_bbox[0]]
    
    new_x = (x_pos[region_bbox[3]-1]- x_pos[region_bbox[1]])/2 + x_pos[region_bbox[1]]
    new_y = (y_pos[region_bbox[2]-1]- y_pos[region_bbox[0]])/2 + y_pos[region_bbox[0]]
    
    if savefig:
        fig.savefig(figpath, dpi=100, transparent=True)
        
    return new_x, new_y, width, height

def checkROIIntensity(fname, elm, coordinates):
    elmmap, x_pos, y_pos = getElmMap(fname, elm)
    
    
def plotBBox(elmmap, box, x_pos, y_pos):
    minr, minc, maxr, maxc = box
    x_st = x_pos[box[1]]
    y_st = y_pos[box[0]]
    w = y_pos[box[2]-1] - y_pos[box[0]]
    h = x_pos[box[3]-1] - x_pos[box[1]]
    rect = mpatches.Rectangle((x_st, y_st), h, w,
            fill=False, edgecolor='red', linewidth=2)
    fig = plt.figure()
    ax = fig.gca()
    ax.pcolor(x_pos, y_pos, elmmap, cmap='gray', shading='auto')
    ax.add_patch(rect)
    return fig

def getElmMap(fname, elm):
    elmmap = []
    with h5py.File(fname, 'r') as dat:
        xrfdata = dat['/MAPS/XRF_roi'][:]
        try:
            ch_idx = dat['/MAPS/channel_names'][:].astype('U13').tolist().index(elm)
            elmmap = xrfdata[ch_idx,:,:]
            x_pos = dat['/MAPS/x_axis'][:]
            y_pos = dat['/MAPS/y_axis'][:]
        except:
            raise ValueError('Invalid element! %s is not in channel list'%(elm))
    return elmmap, x_pos, y_pos


def kmean_analysis(n_clusters, data, random_state, sigma = None, cval = None,
                   plotoption = None, savefig = None, fname = None):
    
    data[np.isnan(data)] = 1e-5
    data[np.isinf(data)] = 1e-5
    
    if sigma is None: sigma = 1
    data_blur = skimage.filters.gaussian(data, sigma = sigma)
    
    km = KMeans(n_clusters = n_clusters,random_state=random_state)
    km.fit(data_blur.reshape(-1,1))
    
    km_label = np.reshape(km.labels_, data.shape)
    
    # sort label based on center
    srtIndex = np.argsort(km.cluster_centers_[:,0])
    for i, s in enumerate(srtIndex):
        km_label[km_label == s] = -(i+1)
    km_label = np.multiply(-1,km_label)-1
    km_bool = km_label.copy()
    km_bool[km_bool > 1] = 1
    
    fig = None
    if plotoption:
        fig, ax = plt.subplots(1,4,figsize=(7,4))
        a = ax[0].imshow(data, cmap = plt.cm.get_cmap('Greys_r'))
        if cval == None:
            cval = a.get_clim()
        else:
            a.set_clim(cval)
        c = ax[1].imshow(data_blur, cmap = plt.cm.get_cmap('inferno'))
        k = ax[2].imshow(km_label, vmin = 0, vmax = n_clusters-1)
        b = ax[3].imshow(np.multiply(data,km_bool), cmap = plt.cm.get_cmap('Greys_r'))
        b.set_clim(cval)
        c.set_clim(cval)
        fig.colorbar(a, ax=ax[0], orientation='horizontal', shrink = 0.8)
        fig.colorbar(c, ax = ax[1], orientation='horizontal', shrink = 0.8)
        fig.colorbar(k, ax = ax[2], orientation='horizontal', shrink = 0.8)
        fig.colorbar(b, ax = ax[3], orientation = 'horizontal', shrink = 0.8)
        
        
        map_label = ['data','blur', 'blur-kmean', 'data * kmean']
        for ax_, l in zip(ax, map_label):
            ax_.axis('off')
            ax_.axis('equal')
            ax_.set_title(l)
        plt.tight_layout()
        plt.show(block=False)
        
        if (savefig == 1) & (fname is not None):
            fig.savefig(fname, dpi = 300)
    
    return km_label, km_bool, fig


def phaseCorrelate(image1, image2):
    fft_array1 = fft2(image1)
    fft_array2 = fft2(image2)

    shape = image1.shape
    c = abs(ifft2(fft_array1 * fft_array2.conjugate() / (abs(fft_array1) * abs(fft_array2))))
    t0, t1 = np.unravel_index(np.argmax(c), image1.shape)
    if t0 > shape[0] // 2:
        t0 -= shape[0]
    if t1 > shape[1] // 2:
        t1 -= shape[1]
    return t0, t1




