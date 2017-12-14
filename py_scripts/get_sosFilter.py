''' 
	Script to design butterworth filter bank. A text file with a c definition of the filter bank is created. 
	Also, given an input signal the average power of each filter's output is computed for validating the design. 

	Author: Dean Richert
	Date: 31/10/2017
'''

from scipy import signal as sig
import numpy as np
from decimal import Decimal
import matplotlib.pyplot as plt

def add_sos(label,sos):
	global sos_str, filterBank_str, biquad_str
	sos_str += "BiQuad filter_" + label + "[FILTER_ORDER] = \n{\n"
	filterBank_str += " {.sos=filter_" + label + "},\n"
	biquad_str = ''
	for section in sos:
		add_biquad(section[0:3],section[3:])
	sos_str += biquad_str + "};\n\n"
	
def add_biquad(b,a):
	check_stability(a)
	global biquad_str
	biquad_str += " {.b={(float)" + str(Decimal.from_float(b[0])) + ",(float)" + str(Decimal.from_float(b[1])) + ",(float)" + str(Decimal.from_float(b[2])) + "},\n"
	biquad_str += "  .a={(float)" + str(Decimal.from_float(a[0])) + ",(float)" + str(Decimal.from_float(a[1])) + ",(float)" + str(Decimal.from_float(a[2])) + "},\n"
	biquad_str += "  .y={0.0,0.0}, \n  .x={0.0,0.0}},\n"


def check_stability(a):
	poles = np.roots(np.float32(a))
	if np.abs(poles[0]) > 1.0 or np.abs(poles[1]) > 1.0:
		print "filter not stable in 32-bit representation"

f = open('filterBankDef_c.txt', 'w')

fs = 40000
#N = 10
#freq = 2000
#t = np.arange(N)
#x = (4096/2)*(np.sin(2 * np.pi * freq * t / fs) + 1)
#x = x.astype(int)

nyq = 0.5 * fs

band_centres = [1e3*2**idx for idx in range(-5,5)]
band_limits = [band_centres[0]/2**0.5] + [freq*2**0.5 for freq in band_centres]
band_limits = sorted(list(set([int(round(min(freq,nyq))) for freq in band_limits])))

order = 6

filterBank_str = "Filter filterBank[NUM_FILTERS] = \n{\n"
sos_str = ''
biquad_str = ''

# design the bp filters
for j in range(0,len(band_limits)-1):
	sos = sig.butter(order, [band_limits[j]/nyq, band_limits[j+1]/nyq], btype='band', output='sos')
	#y = sig.sosfilt(sos,x)
	#print np.sum(y**2)/N
	add_sos(str(band_limits[j]) + "_" + str(band_limits[j+1]),sos)

# write the results to file	
f.write(sos_str + filterBank_str + "};\n")