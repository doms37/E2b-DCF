#%matplotlib inline

import os
import cv2
import numpy as np
from joblib import Parallel, delayed
import matplotlib.pyplot as plt
from matplotlib.pylab import subplot
from matplotlib.colors import LogNorm
import matplotlib.cm as cm
from matplotlib.widgets import SpanSelector
from tqdm.auto import tqdm
from scipy.optimize import leastsq
from typing import List


# Set environment variables for OpenCV
os.environ['OPENCV_LOG_LEVEL'] = 'FATAL'
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = "-8"

video_file = "/Users/domswift/Documents/GitHub/E2_DCF/build_DDM/data/DDM_two_particle/x10/1x1000_0.5x10000.avi" # Change this to the name of the video file you want to analyse
pixelSize = 0.469 #micrometere/pixel(in micrometre)

# 0.229 for x20 lens however my own calc says 0.215
# 0.469 for x10 lens


class ImageStack:
    def __init__(self, filename: str, channel=None):
        self.filename = filename

        # load the video file in a cv2 object
        self.video = cv2.VideoCapture(filename)

        if not self.video.isOpened():
            raise ValueError('File path likely incorrect, failed to open.')

        property_id = int(cv2.CAP_PROP_FRAME_COUNT)

        # get the number of frames
        self.frame_count = int(self.video.get(property_id))
        # get the fps
        self.fps = self.video.get(cv2.CAP_PROP_FPS)
        # store the specified colour channel (if any)
        self.channel = channel

        # read first frame to determine the shape (keep original shape)
        self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.shape = self[0].shape

    def __len__(self):
        return self.frame_count
            
    def __getitem__(self, t):
        """Fetches frame at specified index (can handle non-integer index)"""
        # handle negative indices
        if t < 0:
            t= len(self) + t - 1
        
        # check index is in range
        assert t < self.frame_count
        self.video.set(cv2.CAP_PROP_POS_FRAMES, t - 1)
        success, image = self.video.read()

        if self.channel is not None:
            return image[...,self.channel]
        if image is not None:
            return image.mean(axis=2).astype(int)
        self.shape = self[0].shape
    
    def pre_load_stack(self):
        """Load all frames into a numpy array which is pickleable."""
        # load the first frame to determine whether it is RGB or grayscale
        first_frame = self[0]

        # handle grayscale or RGB frames (2 or 3 dimensions)
        if len(first_frame.shape) == 2:  # Grayscale
            frames = np.zeros((self.frame_count, *first_frame.shape), dtype=np.uint8)
        elif len(first_frame.shape) == 3:  # RGB
            frames = np.zeros((self.frame_count, *first_frame.shape), dtype=np.uint8)
        else:
            raise ValueError(f"Unsupported frame shape: {first_frame.shape}")

        # load all frames into the pre-constructed array
        for i in range(self.frame_count):
            frames[i] = self[i]
        return frames
    
    def verify_frames(self):
        """Verifies that the frames stored in preloaded_stack match those from the stack object."""

        # load preloaded stack
        preloaded_stack = self.pre_load_stack()

        # loop through each frame and verify data
        for i in range(self.frame_count):
            # compare corresponding frames in the preloaded stack and the stack
            if not np.array_equal(preloaded_stack[i], self[i]):
                print(f"Frames at index {i} do not match!")
                return False
        
        print("All frames match correctly.")
        return True

class ImageStackOriginal(object):
    def __init__(self, filename, channel = None):
        # Initialize the ImageStack object
        self.filename = filename
        self.video = cv2.VideoCapture(filename)  # Open the video file
        property_id = int(cv2.CAP_PROP_FRAME_COUNT)  
        length = int(self.video.get(property_id))  # Get the number of frames in the video
        self.frame_count = length  # Store the number of frames
        self.fps = self.video.get(cv2.CAP_PROP_FPS)  # Get the frames per second of the video
        self.channel = channel  # Store the specified channel
        self.shape = self[0].shape

    def __len__(self):
        return self.frame_count  # Return the number of frames in the video
            
    def __getitem__(self, t):
        if t<0: t= len(self)+t-1  # Handle negative indices
        assert t < self.frame_count  # Check if the index is within the range
        self.video.set(cv2.CAP_PROP_POS_FRAMES, t-1)  # Set the position of the video to the desired frame
        success, image = self.video.read()  # Read the frame

        if self.channel is not None:
            return image[...,self.channel]  # Return the specified channel of the frame
        if image is not None:
            return image.mean(axis=2).astype(int)  # Return the grayscale version of the frame
        self.shape = self[0].shape  # Get the shape of the first frame


stack = ImageStack(video_file)
preloaded_stack = stack.pre_load_stack()

stack.verify_frames()
"""
plt.figure(figsize=(14,4))
plt.suptitle('Checking the Image Stack')
subplot(1,3,1).imshow(stack[0], 'gray')
subplot(1,3,1).set_title('First Frame')
subplot(1,3,2).imshow(stack[-1], 'gray')
subplot(1,3,2).set_title('Last Frame')
subplot(1,3,3).imshow(np.abs(stack[-1] - stack[0]).astype(float), 'gray')
subplot(1,3,3).set_title('Difference')
"""

def spectrumDiff(im0, im1):
    """
    Computes squared modulus of 2D Fourier Transform of difference between im0 and im1
    Args:
        im0: matrix type object for frame at time t
        im1: matrix type object for frame at time t + tau
    """
    return np.abs(np.fft.fft2(im1-im0.astype(float)))**2

"""
plt.figure(figsize=(14,4))
plt.suptitle('Spectra for different lag times')
"""

# find 99th percentile frequency max_v
max_v = np.percentile(np.fft.fftshift(spectrumDiff(stack[0], stack[3])),99)

# produce 3 heat maps (dark is low frequency, light is high frequency)
frame_count = stack.frame_count
fps = stack.fps
"""
subplot(1,3,1).imshow(np.fft.fftshift(spectrumDiff(stack[0], stack[3])), 'hot',vmin=0, vmax=max_v)
subplot(1,3,1).set_title(f'tau = {round(3 / fps, 2)}s')
subplot(1,3,2).imshow(np.fft.fftshift(spectrumDiff(stack[0], stack[30])), 'hot',vmin=0, vmax=max_v)
subplot(1,3,2).set_title(f'tau = {round(30 / fps, 2)}s')
subplot(1,3,3).imshow(np.fft.fftshift(spectrumDiff(stack[0], stack[-1])), 'hot',vmin=0, vmax=max_v)
subplot(1,3,3).set_title(f'tau = {round((frame_count - 1) / fps, 2)}s')
"""


def timeAveraged(frames: np.ndarray, dframes: int, maxNCouples: int=20):
    """
    Does at most maxNCouples spectreDiff on regularly spaced couples of images. 
    Args:
        frames: numpy array of frames loaded in advance
        dframes: interval between frames (integer)
        maxNCouples: maximum number of couples to average over
    """
    # create array of initial times (the 'im0' in spectrumDiff) of length maxNCouples AT MOST
    # evenly spaced in increments of 'increment'
    increment = max([(frames.shape[0] - dframes) / maxNCouples, 1])
    initialTimes = np.arange(0, frames.shape[0] - dframes, increment)

    avgFFT = np.zeros(frames.shape[1:])
    failed = 0
    for t in initialTimes:
        t = np.floor(t).astype(int)

        im0 = frames[t]
        im1 = frames[t+dframes]
        if im0 is None or im1 is None:
            failed +=1
            continue
        avgFFT += spectrumDiff(im0, im1)
    return avgFFT / (initialTimes.size - failed)


def timeAveraged_old(stack, dt, maxNCouples=20):
    """Does at most maxNCouples spectreDiff on regularly spaced couples of images. 
    Separation within couple is dt."""
    #Spread initial times over the available range
    increment = max([(len(stack)-dt)/maxNCouples, 1])
    initialTimes = np.arange(0, len(stack)-dt, increment)
    #perform the time average
    avgFFT = np.zeros(stack.shape)
    failed = 0
    for t in initialTimes:
        im0 = stack[t]
        im1 = stack[t+dt]
        if im0 is None or im1 is None:
            failed +=1
            continue
        avgFFT += spectrumDiff(im0, im1)
    return avgFFT / (len(initialTimes)-failed)

dframes = 5
maxNCouples = 10

original_stack = ImageStackOriginal(video_file)

new_avg = timeAveraged(preloaded_stack, dframes, maxNCouples)
old_avg = timeAveraged_old(stack, dframes, maxNCouples)
original_avg = timeAveraged_old(original_stack, dframes, maxNCouples)

same = np.array_equal(new_avg, old_avg)
print(same)

#plt.figure(figsize=(14,4))
#plt.suptitle('Time Averaged Spectra')

# create numpy array of frames
# preloaded_stack = stack.pre_load_stack()

timeAverage_3 = timeAveraged(preloaded_stack, 3, 5)
timeAverage_30 = timeAveraged(preloaded_stack, 30, 5)
timeAverage_300 = timeAveraged(preloaded_stack, frame_count - 1, 5)

"""
subplot(1,3,1).imshow(np.fft.fftshift(timeAverage_3), 'hot',vmin=0, vmax=max_v)
subplot(1,3,1).set_title(f'Time Average (dt = {round(3 / fps, 2)}s)')
subplot(1,3,2).imshow(np.fft.fftshift(timeAverage_30), 'hot',vmin=0, vmax=max_v)
subplot(1,3,2).set_title(f'Time Average (dt = {round(30 / fps, 2)}s)')
subplot(1,3,3).imshow(np.fft.fftshift(timeAverage_300), 'hot',vmin=0, vmax=max_v)
subplot(1,3,3).set_title(f'Time Average (dt = {round((frame_count - 1) / fps, 2)}s)')
"""

class RadialAverager(object):
    """Radial average of a 2D array centred on (0,0), like the result of fft2d."""
    def __init__(self, shape):
        """A RadialAverager instance can process only arrays of a given shape, fixed at instanciation."""
        assert len(shape)==2
        #matrix of distances
        self.dists = np.sqrt(np.fft.fftfreq(shape[0])[:,None]**2 +  np.fft.fftfreq(shape[1])[None,:]**2)
        #dump the cross
        self.dists[0] = 0
        self.dists[:,0] = 0
        #discretize distances into bins
        self.bins = np.arange(max(shape)/2+1)/float(max(shape))
        #number of pixels at each distance
        self.hd = np.histogram(self.dists, self.bins)[0]
    
    def __call__(self, im):
        """Perform and return the radial average of the specrum 'im'"""
        assert im.shape == self.dists.shape
        hw = np.histogram(self.dists, self.bins, weights=im)[0]
        return hw/self.hd

#plt.figure(figsize=(5,5))

# ra is now a callable function which performs the Radial Averaging on a 2D array of a fourier transform
ra = RadialAverager(stack.shape)

"""
# for example, perform ra on the timeAverage between 1st and 30th frame
plt.plot(ra(timeAverage_30))
plt.xscale('log')
plt.yscale('log')
plt.xlabel('q [px$^{-1}$]')
plt.ylabel('Intensity [a.u.]')
plt.title('Radial Average of the Time Averaged Spectrum')
"""

def logSpaced(L: float, pointsPerDecade: int=15) -> List[int]:
    """Generate an array of log spaced integers smaller than L"""
    nbdecades = np.log10(L)
    return np.unique(np.logspace(
        start=0, stop=nbdecades, 
        num=int(nbdecades * pointsPerDecade), 
        base=10, endpoint=False
        ).astype(int))


def calculate_isf_original(stack, idts, maxNCouples=1000):
    """Perform time averaged and radial averaged DDM for given time intervals.
    Returns isf"""
    ra = RadialAverager(stack.shape)
    isf = np.zeros((len(idts), len(ra.hd)))
    for i, idt in tqdm(enumerate(idts), total=len(idts)):
        isf[i] = ra(timeAveraged(stack, idt, maxNCouples))
    return isf

def calculate_isf(stack: ImageStack, preloaded_stack: np.ndarray, idts: List[float], maxNCouples: int = 1000, n_jobs=-1) -> np.ndarray:
    """
    Perform time-averaged and radial-averaged DDM for given time intervals.
    Returns ISF (Intermediate Scattering Function).

    Args:
        stack: ImageStack object (from cv2.VideoCapture)
        preloaded_stack: numpy array of frames (required for pickling)
        idts: List of integer rounded indices (within range) to specify
              which frames to time-average between
        maxNCouples: Maximum number of pairs to perform time averaging over
        n_jobs: Number of parallel jobs to run (set to -1 for all cores)
    """
    # create instance of radial averager callable
    ra = RadialAverager(stack.shape)
    
    # parallelise the time averaging
    with Parallel(n_jobs=n_jobs, backend='threading') as parallel:
        time_avg_results = parallel(delayed(timeAveraged)(preloaded_stack, idt, maxNCouples) for idt in idts)

    # parallelize the radial averaging
    with Parallel(n_jobs=n_jobs, backend='threading') as parallel:
        isf = np.array(parallel(delayed(ra)(ta) for ta in time_avg_results))

    return isf


# number of points to sample between each power of 10 in time intervals
pointsPerDecade = 30

# recommended values: 10 for speed, 300 for accuracy
maxNCouples = 10

# generate list of indices log spaced
idts = logSpaced(stack.frame_count, pointsPerDecade)

# converting the idts list of indices back to continuous time
dts = idts / stack.fps
ISF = calculate_isf(stack, preloaded_stack, idts, maxNCouples)


qs = 2*np.pi/(2*ISF.shape[-1]*pixelSize) * np.arange(ISF.shape[-1])
tmax = -1

"""
plt.figure(figsize=(5,5))
ISF_transposed = np.transpose(ISF)
plt.imshow(ISF_transposed, cmap='viridis', aspect='auto', extent=[dts[0], dts[-1], qs[-1], qs[0]], norm=LogNorm())
plt.colorbar(label='I(q,$\\tau$),[a.u.]')
plt.title('Image Structure Function I(q,$\\tau$)')
plt.xlabel('Lag time ($\\tau$) [s]')
plt.ylabel('Spatial Frequency (q) [$\\mu m ^{-1}$]')
plt.show()
"""

LogISF = lambda p, dts: np.log(np.maximum(p[0] * (1 - np.exp(-dts / p[1])) + p[2]* (1 - np.exp(-dts / p[3])) + p[4], 1e-10))


import numpy as np


params = np.zeros((ISF.shape[-1], 5))
matrixfit = np.zeros(ISF[:tmax].T.shape)

for iq, ddm in enumerate(ISF[:tmax].T):
    
    params[iq] = leastsq(
        # function to minimize
        lambda p, dts, logd: LogISF(p, dts) - logd,
        # initial parameters
        [np.ptp(ISF)/2, ddm.min(), np.ptp(ISF)/2, ddm.max(), 1],
        # data on which to perform minimization
        args=(dts[:tmax], np.log(ddm))
    )[0]

    # Ensure non-negative values
    matrixfit[iq] = np.exp(LogISF(params[iq], dts[:tmax]))

    


def onselect(xmin, xmax):
    global iqmin, iqmax
    iqmin= np.searchsorted(qs, xmin)
    iqmax = np.searchsorted(qs, xmax)
    print(f"Selected range: {qs[iqmin]:.2f} to {qs[iqmax]:.2f}")

fig, ax = plt.subplots(figsize=(8, 6))
ax.plot(qs, params[:, 2], 'o')
ax.set_xscale('log')
ax.set_yscale('log')
ax.set_xlabel(r'$q\ [\mu m^{-1}$]')
ax.set_ylabel(r'Characteristic time $\tau_c\ [s]$')
ax.set_title('Click and drag to select a valid range of q values')

span = SpanSelector(ax, onselect, 'horizontal', useblit=True, interactive=True, props=dict(alpha=0.5, facecolor='red'))
plt.show()


# Only use if you want to select the range of q manually

#iqmin = np.where(qs > 1.2)[0][0]
#iqmax = np.where(qs < 1.8)[0][-1]

import matplotlib.pyplot as plt

plt.figure(figsize=(8,6))
plt.title('Fit parameters A(q) and B(q)')
plt.plot(qs, params[:,0], 'o', label="A_1(q)")
plt.plot(qs, params[:,2], 'o', label="A_2(q)")
plt.plot(qs, params[:,4], 'o', label="B(q)")

plt.xscale('log')
plt.yscale('log')
plt.xlabel(r'$q\ [\mu m^{-1}]$')
plt.ylabel(r'$A(q),\, B(q)$')

plt.axvspan(qs[iqmin], qs[iqmax], color=(0.9,0.9,0.9))
plt.legend()
plt.ylim((1e3,1e11))


"""
# Calculate Residual Sum of Squares (RSS) between the data and the model predicted by theory of alpha = 2. This serves as the relative error in slope.
RSS = 0
no_q = 0

for i in range (len(qs)):
    if i <= iqmax and i >= iqmin:
        no_q += 1
        RSS += abs(params[i,2] - 1/(X*np.array(qs[i])**alpha))**2

# Under the assumption that 3 restrictions on degrees of freedom i.e. that we fit 3 parameters, define variance
var = 1/(no_q - 3) * RSS

# The error in the gradient is then calculcated using this and the covariant matrix from leastsq:
cov_x =leastsq(
    lambda p, q, td: p[0] - p[1]*np.log(np.abs(q)) - np.log(np.abs(td)),
    [1,2],
    args=(qs[iqmin:iqmax], params[iqmin:iqmax,2]),
    full_output= True
    )[1]

delta_D = np.sqrt(var * (cov_x[0,0] + cov_x[1,1]))
"""

plt.figure(figsize=(8,6))
# Plotting the characteristic time paramater for each exponential for all q in the range
plt.plot(qs, params[:,1], 'o')
plt.plot(qs, params[:,3], 'o')

plt.xscale('log')
plt.yscale('log')

plt.xlabel(r'$q\,(\mu m^{-1})$')
plt.ylabel(r'Characteristic time $\tau_c (s)$')

plt.axvspan(qs[iqmin], qs[iqmax], color=(0.9,0.9,0.9))

# Plot fit lines for each characteristic time individually
X, alpha_1 = leastsq(
    lambda p, q, td: p[0] - p[1]*np.log(np.abs(q)) - np.log(np.abs(td)),
    [1,2],
    args=(qs[iqmin:iqmax], params[iqmin:iqmax,2]),
    full_output= True
    )[0]
X= np.exp(-X)
plt.plot([qs[iqmin], qs[iqmax]], 1/(X*np.array([qs[iqmin], qs[iqmax]])**alpha_1), '-r')

Y, alpha_2 = leastsq(
    lambda p, q, td: p[0] - p[1]*np.log(np.abs(q)) - np.log(np.abs(td)),
    [1,2],
    args=(qs[iqmin:iqmax], params[iqmin:iqmax,2]),
    full_output= True
    )[0]

Y= np.exp(-Y)
plt.plot([qs[iqmin], qs[iqmax]], 1/(Y*np.array([qs[iqmin], qs[iqmax]])**alpha_2), '-r')

print(f"alpha_1 = {alpha_1:.05f}")
print(f"X = {X:.02f}")

print(f"alpha_2 = {alpha_2:.05f}")
print(f"Y = {Y:.02f}")

delta_D = 0
D_1 = np.exp(-leastsq(
    lambda p, q, td: p[0] - p[1]*np.log(np.abs(q)) - np.log(np.abs(td)),
    [1,2],
    args=(qs[iqmin:iqmax], params[iqmin:iqmax,2])
    )[0][0])
plt.plot([qs[iqmin], qs[iqmax]], 1/(D_1*np.array([qs[iqmin], qs[iqmax]])**2), '-r')
print(f"D = {D_1:.05f}",'±', f"{delta_D:.05f}µm²/s")

D_2 = np.exp(-leastsq(
    lambda p, q, td: p[0] - p[3]*np.log(np.abs(q)) - np.log(np.abs(td)),
    [1,2],
    args=(qs[iqmin:iqmax], params[iqmin:iqmax,2])
    )[0][0])
plt.plot([qs[iqmin], qs[iqmax]], 1/(D_1*np.array([qs[iqmin], qs[iqmax]])**2), '-r')
print(f"D = {D_2:.05f}",'±', f"{delta_D:.05f}µm²/s")

kB = 1.38e-23
T = 300
mu = 10e-4
del_T = 0.1
predicted_a_1 = kB*T/(3*np.pi*mu*D_1) *1e12*1e6

del_a_1 = predicted_a_1 * np.sqrt((delta_D/D_1)**2 + (del_T/T)**2)
print(f"Diameter_1 = {predicted_a_1:.05f} ± {del_a_1:.05f} µm")

predicted_a_2 = kB*T/(3*np.pi*mu*D_2) *1e12*1e6

del_a_2 = predicted_a_2 * np.sqrt((delta_D/D_2)**2 + (del_T/T)**2)
print(f"Diameter_1 = {predicted_a_2:.05f} ± {del_a_2:.05f} µm")


