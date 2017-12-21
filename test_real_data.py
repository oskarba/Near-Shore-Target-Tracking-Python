import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import tracking
import simulation
import visualization
import track_initiation

import pickle

# Load real data -------------------------------------------
def load_pkl(pkl_file):
    obj = None
    with open(pkl_file, 'rb') as f:
        obj = pickle.load(f,encoding='latin1')
    return obj

z_file = 'measurements_out.pkl'
ais_file = 'ais_data_out.pkl'
measurements_all = load_pkl(z_file)
ais = load_pkl(ais_file)

measurements_all_new = []
for measurements in measurements_all:
    measurements_new = []
    for measurement in measurements:
        timestamp, value, covariance = measurement
        measurement_new = tracking.Measurement(value, timestamp, covariance)
        measurements_new.append(measurement_new)
    measurements_all_new.append(measurements_new)


for mmsi, data in ais.items():
    if mmsi != 257999459:
        time1, true_state1 = data
    else:
        time2, true_state2 = data

# Real data loaded -----------------------------------------

# Global constants
clutter_density = 2e-5
radar_range = 1000
dt = 2.88

# Kalman filter stuff
q = 0.25                  # Process noise strength squared
r = 50                    # Measurement noise strength squared
H = np.array([[1, 0, 0, 0], [0, 0, 1, 0]])
R = r*np.identity(2)      # Measurement covariance
F, Q = tracking.DWNAModel.model(dt, q)

#PDA constants
P_G = 0.99
P_D = 0.9

# -----------------------------------------------

# Define initiation and termination parameters
# IPDA
p11 = 0.98          # Survival probability
p21 = 0             # Probability of birth
P_Markov = np.array([[p11, 1 - p11], [p21, 1 - p21]])
initiate_thresh = 0.98
terminate_thresh = 0.10
# MofN
N_test = 6
M_req = 4
N_terminate = 3

# Set up tracking system
v_max = 10*dt
radar = simulation.SquareRadar(radar_range, clutter_density, P_D, R)
gate = tracking.TrackGate(P_G, v_max)
target_model = tracking.DWNAModel(q)

initiation_type = 0   # 0: MofN     else: IPDA
if initiation_type == 1:
    PDAF_tracker = tracking.PDAFTracker(P_D, target_model, gate)
    M_of_N = track_initiation.MOfNInitiation(M_req, N_test, PDAF_tracker, gate)
    track_termination = tracking.TrackTerminatorMofN(N_terminate)
    track_manager = tracking.Manager(PDAF_tracker, M_of_N, track_termination)
else:
    IPDAF_tracker = tracking.IPDAFTracker(P_D, target_model, gate, P_Markov, gate.gamma)
    IPDAInitiation = track_initiation.IPDAInitiation(initiate_thresh, terminate_thresh, IPDAF_tracker, gate)
    track_termination = tracking.TrackTerminatorIPDA(terminate_thresh)
    track_manager = tracking.Manager(IPDAF_tracker, IPDAInitiation, track_termination)



# Run tracking
for k, measurements in enumerate(measurements_all_new):
    track_manager.step(measurements)
    if k%10 == 0:
        print(k)

for track_id, state_list in track_manager.track_file.items():
    states = np.array([est.est_posterior for est in state_list])
    time_states = np.array([est.timestamp*10 for est in state_list])
    # for time in time_states:
    #     print(str("%.2f" % (time/10)))


# Calculate speed
# v_arr = []
# for i, state in enumerate(true_state2):
#     if i == 0:
#         continue
#     dx = state[2] - true_state2[i - 1, 2]
#     dy = state[0] - true_state2[i-1, 0]
#     dt = time2[i] - time2[i-1]
#     vx = dx/dt
#     vy = dy / dt
#     v_arr.append(np.hypot(vx,vy))
#     print(dt, vx, vy)
#
# plt.plot(v_arr)

vx_avg = (true_state2[-1, 0] - true_state2[0, 0])/(time2[-1] - time2[0])
vy_avg = (true_state2[-1, 2] - true_state2[0, 2])/(time2[-1] - time2[0])
print(vx_avg, vy_avg)

# ------------------------------------------------------------------------------

# Plot
fig, ax = visualization.plot_measurements(measurements_all_new)

ax.plot(true_state1[:, 2], true_state1[:, 0], 'C1', label='Ownship (Telemetron)')
ax.plot(true_state1[0, 2], true_state1[0, 0], 'C1o')
ax.plot(true_state2[:, 2], true_state2[:, 0], 'k', label='True target')
ax.plot(true_state2[0, 2], true_state2[0, 0], 'ko')
visualization.plot_track_pos(track_manager.track_file, ax, 'r')
ax.set_xlim(-500, 1500)
ax.set_ylim(-1800, -100)
ax.set_xlabel('East[m]')
ax.set_ylabel('North[m]')
#ax.set_title('Track position with sample rate: 2/s')
ax.set_title('AIS and radar data')
ax.legend(loc="upper left")

plt.show()
