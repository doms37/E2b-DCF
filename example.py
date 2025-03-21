from DDM_Fourier import DDM_Fourier

filepath = "/Users/domswift/Documents/GitHub/E2_DCF/build_DDM/data/DDM_initial/x10/0.5micron_x5000_150fps_brightest.avi"

pixel_size = 0.229
example = DDM_Fourier(filepath=filepath, pixel_size=pixel_size, particle_size=0.75, renormalise=True)

print(example.frames[0])

# number of points to sample between each power of 10 in time intervals
pointsPerDecade = 60
# recommended values: 10 for speed, 300 for accuracy
maxNCouples = 30

# generate list of indices log spaced
idts = example.logSpaced(pointsPerDecade)

example.calculate_isf(idts, maxNCouples, plot_heat_map=False)

ISF = example.isf

example.FFT_temporal(ISF, q_selected=0.7)

# example.BrownianCorrelation(ISF, beta_guess=1.)

# example.BrownianCorrelationSubDiffusive(ISF, q_fixed=1.)

# example.TwoParticleCorrelation(ISF, bottom=0., top=100.)
