import numpy as np
import matplotlib.pyplot as plt

from scipy.interpolate import interp1d #spline

#T = np.array([-1,2,5,8,11])
#power = np.array([6.25,6.25,6.25,6.25,2.25])

#xnew = np.linspace(T.min(),T.max(),500) #300 represents number of points to make between T.min and T.max

#power_smooth = spline(T,power,xnew)

fig, ax1 = plt.subplots()
#t = np.arange(0.01, 10.0, 0.01)
#s1 = np.exp(t)
#ax1.plot(t, s1, 'b-')
#ax1.set_xlabel('time (s)')
# Make the y-axis label, ticks and tick labels match the line color.
#ax1.set_ylabel('exp', color='b')
ax1.tick_params('y', colors='b')
ax1.set_ylabel('Capability', color='b')
ax1.set_xlabel(r'In-network processing $\rightarrow$', color='k')
ax1.get_xaxis().set_ticklabels([])
ax1.get_yaxis().set_ticklabels(['small data','delay tolerant','big data','time critical'])
ax1.set_yticks([0,0.25,4.25,4.5])
ax1.set_ylim(0,4.5)

ax2 = ax1.twinx()
#s2 = np.sin(2 * np.pi * t)
#ax2.plot(t, s2, 'r.')
ax2.set_ylabel('Benefit of LoRaWAN', color='g')
ax2.tick_params('y', colors='g')
ax2.get_xaxis().set_ticklabels([])
ax2.get_yaxis().set_ticklabels([])
ax2.set_ylim(0,4.5)


ax1.plot([1,10,16],[1.25,4.25,4.25], linestyle='-', marker='', color='b')
ax1.bar([0,1,4,7,10,13,16],[0,1,2,3,4,4,4], color='b')
ax2.plot([1,8,17],[4.25,4.25,0], linestyle='-', marker='', color='g')
ax2.bar([2,5,8,11,14,17],[4,4,4,2.6,1.2,0], color='g')

plt.show()




#fig.tight_layout()
#plt.show()