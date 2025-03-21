import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from scipy import stats
import os
import re
import csv

kB = 1.38e-23
visc = 8.9e-4
T = 300

class DLS:
    def __init__(self, dir: str, noise_freq: float=100.):
        self.dir = dir
        self.noise_freq = noise_freq
        self.tau_vals = []

        self.relative_q_errors = {
            '26.6': 0.057,
            '30.0': 0.05,
            '35.0': 0.037,
            '40.0': 0.029,
            '45.0': 0.024,
            '48.0': 0.02,
            '50.0': 0.019
        }

        # set sampling frequency
        for entry in os.scandir(dir):
            if entry.is_file():
                filename = entry.path
                data = np.loadtxt(filename, delimiter='\t', skiprows=3)
                self.sample_freq = 1000 / (data[1, 0] - data[0, 0])
                break
    
    def extract_degree_from_filename(self, filename: str):
        """
        Extract degree value from filename. Assumes format '26.6deg.prn'
        """
        match = re.search(r'(\d+\.\d+)deg', filename)
        if match:
            return match.group(1)
        else:
            return None
    
    def AutoCorrelation(self, lin_range: int=30, exp_range: int=500):
        """
        Args:
            lin_range: number of points to use for linear plot
            exp_range: number of points to use for exponential plot
        """
        for entry in os.scandir(self.dir):
            if entry.is_file():
                filename = entry.path
                
                data = np.loadtxt(filename, delimiter='\t', skiprows=3)
                t = data[:, 0]
                voltage = data[:, 1]

                # create bandstop filter
                b, a = butter(2, [self.noise_freq - 1, self.noise_freq + 1], btype='bandstop', fs=self.sample_freq)
                voltage_filtered = filtfilt(b, a, voltage)

                # perform autocorrelation
                N = len(voltage_filtered)
                ac = np.zeros(N-1)
                m = np.mean(voltage_filtered)

                for j in range(1, N):
                    ac[j-1] = np.mean((voltage_filtered[0:N-j] - m) * (voltage_filtered[j:N] - m))

                # fit logarithm of autocorrelation for tau
                x = np.arange(lin_range)
                y = np.log(ac[:lin_range])

                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                tau = -2 / slope

                # calculate error in tau from std
                tau_error = abs(2 / slope**2) * std_err

                degree = self.extract_degree_from_filename(filename)
                relative_q_error = self.relative_q_errors[degree]
                q = (4 * np.pi * np.sin(np.radians(float(degree)) / 2)) / (635e-9)

                # tau is in ms, calculating a in m first, convert to μm after
                particle_size = (kB * T * tau * 1e-3 * q**2) / (3 * np.pi * visc)

                size_error = np.sqrt((tau_error / tau)**2 + (2 * relative_q_error)**2) * particle_size

                # extract degree from the filename
                degree = self.extract_degree_from_filename(filename)
                if degree is not None:
                    self.tau_vals.append((degree, tau, tau_error, particle_size * 1e6, size_error * 1e6))

                # plot results on log scale
                plt.figure(figsize=(10, 6))
                plt.semilogy(x, ac[:lin_range], 'ro', label='Exp data:')
                plt.plot(x, np.exp(slope * x + intercept), linewidth=2, label='Fit - exp(-t/τ)')
                plt.text(2, 0.5, f"$\\tau = {tau:.3f}$", fontsize=12, color='blue')
                plt.xlabel(r'Time [ms]', fontsize=14)
                plt.ylabel(r'$C(t)\ [V^2]$', fontsize=14)
                plt.legend(loc='best', fontsize=14)
                plt.title(f'Correlation function with Exponential Fit (Semi-Log scale): {degree}°', fontsize=14)
                
                plt.show()
                
                # plot results on linear scale
                plt.figure(figsize=(10, 6))
                plt.plot(t[:exp_range], ac[:exp_range], 'ro', markersize=3, label='Exp data')
                plt.plot(t[:exp_range], np.exp(slope * t[:exp_range] + intercept), linewidth=2, label='Fit - exp(-t/τ)')
                plt.text(0.1, 0.2, f"$\\tau = {tau:.3f}$", fontsize=12, color='blue')
                plt.xlabel(r'Time [ms]', fontsize=14)
                plt.ylabel(r'$C(t)\ [V^2]$', fontsize=14)
                plt.legend(loc='best', fontsize=14)
                plt.title(f'Correlation function with Exponential Fit (Linear scale): {degree}°', fontsize=14)
                
                plt.show()

        dir_name = os.path.basename(self.dir)
        csv_filename = f"{dir_name}_taus.csv"

        # save tau values and associated errors to csv
        with open(csv_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([' Degree ° ', ' τ (ms) ', ' Δτ ', ' a (μm) ', ' Δa '])
            writer.writerows(self.tau_vals)
        print(f"Tau values and errors have been saved to '{csv_filename}'")

# Example usage of the class
dls = DLS('DLS_files/1.00micro_1000dil')
dls.AutoCorrelation()  # Computes autocorrelation and saves tau and errors to CSV
