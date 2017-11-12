import numpy as np
import matplotlib.pyplot as plt
import trajectory_tools
import tracking
import simulation
import visualization
import track_initiation


# Global constants
clutter_density = 1e-5
radar_range = 1000

# Initialized target
x0_1 = np.array([100, 4, 0, 5])
x0_2 = np.array([-100, -4, 0, -5])
cov0 = np.diag([10, 0.5, 10, 0.5])

# Time for simulation
dt = 1
t_end = 150
time = np.arange(0, t_end, dt)
K = len(time)             # Num steps

# Kalman filter stuff
q = 0.25                  # Process noise strength squared
r = 50
H = np.array([[1, 0, 0, 0], [0, 0, 1, 0]])
R = r*np.identity(2)      # Measurement covariance
F, Q = tracking.DWNAModel.model(dt, q)


#PDA constants
P_G = 0.99
P_D = 0.9

# Empty state and covariance vectors
x_true = np.zeros((2, 4, K))

# -----------------------------------------------

# Set up tracking system
v_max = 10/dt
radar = simulation.SquareRadar(radar_range, clutter_density, P_D, R)
scan_area = radar.calculate_area(radar_range)
gate = tracking.TrackGate(P_G, v_max)
p11 = 0.98          # Survival probability
p21 = 0             # Probability of birth
P_Markov = np.array([[p11, 1 - p11], [p21, 1 - p21]])
target_model = tracking.DWNAModel(q, P_Markov)
IPDAF_tracker = tracking.IPDAFTracker(P_D, target_model, gate, P_Markov, scan_area)
# N_test = 6
# M_req = 4
# N_terminate = 4
# M_of_N = track_initiation.MOfNInitiation(M_req, N_test, IPDAF_tracker, gate)
# track_termination = tracking.TrackTerminator(N_terminate)
# track_manager = tracking.Manager(IPDAF_tracker, M_of_N, track_termination)

# track_manager = tracking.Manager(PDAF_tracker)

initiate_prob = 0.98
terminate_prob = 0.20
N_terminate = 4
IPDAInitiation = track_initiation.IPDAInitiation(initiate_prob, terminate_prob, IPDAF_tracker, gate)
track_termination = tracking.TrackTerminator(N_terminate)
track_manager = tracking.Manager(IPDAF_tracker, IPDAInitiation, track_termination)

# Generate target trajectory - random turns, constant velocity
traj_tools = trajectory_tools.TrajectoryChange()
for k, t in enumerate(time):
    if k == 0:
        x_true[0, :, k] = x0_1
        x_true[1, :, k] = x0_2.T
    else:
        x_true[0, :, k] = F.dot(x_true[0, :, k - 1])
        x_true[1, :, k] = F.dot(x_true[1, :, k - 1])
        x_true[0, :, k] = traj_tools.randomize_direction(x_true[0, :, k]).reshape(4)
        x_true[1, :, k] = traj_tools.randomize_direction(x_true[1, :, k]).reshape(4)

# Initialize tracks
#first_est_1 = tracking.Estimate(0, x0_1, cov0, is_posterior=True, track_index=0)
#first_est_2 = tracking.Estimate(0, x0_2, cov0, is_posterior=True, track_index=1)
# track_manager.add_new_tracks([[first_est_1], [first_est_2]])

# Run tracking
measurements_all = []
for k, timestamp in enumerate(time):
    measurements = radar.generate_measurements([H.dot(x_true[0, :, k]), H.dot(x_true[1, :, k])], timestamp)
    measurements_all.append(measurements)
    track_manager.step(measurements)

# Plot
fig, ax = visualization.plot_measurements(measurements_all)
ax.plot(x_true[0, 2, :], x_true[0, 0, :], 'k', label='True trajectory 1')
ax.plot(x_true[0, 2, 0], x_true[0, 0, 0], 'ko')
ax.plot(x_true[1, 2, :], x_true[1, 0, :], 'k', label='True trajectory 2')
ax.plot(x_true[1, 2, 0], x_true[1, 0, 0], 'ko')
visualization.plot_track_pos(track_manager.track_file, ax, 'r')
ax.set_xlim(-radar_range, radar_range)
ax.set_ylim(-radar_range, radar_range)
ax.set_xlabel('East[m]')
ax.set_ylabel('North[m]')
ax.set_title('Track position with sample rate: 1/s')
ax.legend()

plt.show()
