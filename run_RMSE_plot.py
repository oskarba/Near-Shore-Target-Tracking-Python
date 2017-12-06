import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import trajectory_tools
import tracking
import simulation
import visualization
import track_initiation


# Global constants
clutter_density = 2e-5
radar_range = 1000

# Initialized target
num_ships = 1
x0_1 = np.array([100, 4, 0, 5])
x0_2 = np.array([-100, -4, 0, -5])
x0 = [x0_1, x0_2]

# Time for simulation
dt = 1
t_end = 30
time = np.arange(0, t_end, dt)
K = len(time)             # Num steps

# Empty state vectors
x_true = np.zeros((num_ships, 4, K))

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
initiate_thresh = 0.90
terminate_thresh = 0.10
# MofN
N_test = 6
M_req = 4
N_terminate = 3

# Set up tracking system
v_max = 10/dt
radar = simulation.SquareRadar(radar_range, clutter_density, P_D, R)
gate = tracking.TrackGate(P_G, v_max)
target_model = tracking.DWNAModel(q)


# Generate target trajectory - random turns, constant velocity
traj_tools = trajectory_tools.TrajectoryChange()
for k, t in enumerate(time):
    for ship in range(num_ships):
        if k == 0:
            x_true[ship, :, k] = x0[ship]
        else:
            x_true[ship, :, k] = F.dot(x_true[ship, :, k - 1])
            x_true[ship, :, k] = traj_tools.randomize_direction(x_true[ship, :, k]).reshape(4)


num_runs = 500
error_arr = []
for run in range(num_runs):
    IPDAF_tracker = tracking.IPDAFTracker(P_D, target_model, gate, P_Markov, gate.gamma)
    IPDAInitiation = track_initiation.IPDAInitiation(initiate_thresh, terminate_thresh, IPDAF_tracker, gate)
    track_termination = tracking.TrackTerminatorIPDA(terminate_thresh)
    track_manager = tracking.Manager(IPDAF_tracker, IPDAInitiation, track_termination)
    # Run tracking
    for k, timestamp in enumerate(time):
        measurements = radar.generate_measurements([H.dot(x_true[ship, :, k]) for ship in range(num_ships)], timestamp)
        track_manager.step(measurements)

    # Error for estimates (One ship)
    for track_id, state_list in track_manager.track_file.items():
        # states = np.array([est.est_posterior for est in state_list])
        error_dic = dict()
        for est in state_list:
            t = est.timestamp
            dist = trajectory_tools.dist(x_true[0, 2, t], x_true[0, 0, t], est.est_posterior[2], est.est_posterior[0])
            error_dic[t] = dist
        error_arr.append(error_dic)
    if run%10==0:
        print(run)


# Plot
fig, ax = visualization.setup_plot(None)
for dic in error_arr:
    list_IPDA = sorted(dic.items())
    xIPDA, yIPDA = zip(*list_IPDA)
    plt.plot(xIPDA, yIPDA)
ax.set_title('Error distance of 500 runs of 30 scans')
ax.set_xlabel('Scan number')
ax.set_ylabel('Distance from real target [m]')
# ax.legend()
for axis in [ax.xaxis, ax.yaxis]:
    axis.set_major_locator(ticker.MaxNLocator(integer=True))
c1 = 25
c2 = 50
plt.plot((0, t_end), (c1, c1), 'k--')
plt.plot((0, t_end), (c2, c2), 'k--')



plt.show()