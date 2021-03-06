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
t_end = 500
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
initiate_thresh = 0.995
terminate_thresh = 0.10
# MofN
N_test = 6
M_req = 5
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

# Run true detected tracks demo
scans_MofN = dict()
scans_IPDA = dict()
num_runs = 500
num_scans = K
for method in range(2):
    for run in range(num_runs):
        # Run tracking
        if method == 0:
            PDAF_tracker = tracking.PDAFTracker(P_D, target_model, gate)
            M_of_N = track_initiation.MOfNInitiation(M_req, N_test, PDAF_tracker, gate)
            track_termination = tracking.TrackTerminatorMofN(N_terminate)
            track_manager = tracking.Manager(PDAF_tracker, M_of_N, track_termination)
        else:
            IPDAF_tracker = tracking.IPDAFTracker(P_D, target_model, gate, P_Markov, gate.gamma)
            IPDAInitiation = track_initiation.IPDAInitiation(initiate_thresh, terminate_thresh, IPDAF_tracker, gate)
            track_termination = tracking.TrackTerminatorIPDA(terminate_thresh)
            track_manager = tracking.Manager(IPDAF_tracker, IPDAInitiation, track_termination)

        tracks_spotted = set()
        for k, timestamp in enumerate(time):
            measurements = radar.generate_measurements([H.dot(x_true[ship, :, k]) for ship in range(num_ships)], timestamp)
            track_manager.step(measurements)

            # Check if true tracks have been detected
            for track_id, state_list in track_manager.track_file.items():
                states = np.array([est.est_posterior for est in state_list])
                for ship in range(num_ships):
                    if trajectory_tools.dist(x_true[ship, 2, k], x_true[ship, 0, k], states[-1, 2], states[-1, 0]) < 50:
                        tracks_spotted.add(ship)
                        break
            if len(tracks_spotted) == num_ships:
                num_scans = k
                if method == 0:
                    if k+1 in scans_MofN:
                        scans_MofN[k + 1] += 1
                    else:
                        scans_MofN[k + 1] = 1
                else:
                    if k+1 in scans_IPDA:
                        scans_IPDA[k + 1] += 1
                    else:
                        scans_IPDA[k + 1] = 1
                break

        # Print time for debugging purposes
        if run % 50 == 0:
            print(run)

max_key = max(max(scans_MofN.keys()), max(scans_IPDA.keys()))

for scans in [scans_MofN, scans_IPDA]:
    for key in range(1, max_key + 1):
        if key not in scans:
            scans[key] = 0

    last = 0
    for key in sorted(scans.keys()):
        last = last + scans[key]
        scans[key] = last

list_MofN = sorted(scans_MofN.items())
list_IPDA = sorted(scans_IPDA.items())
xMofN, yMofN = zip(*list_MofN)
xIPDA, yIPDA = zip(*list_IPDA)

# Plot
fig, ax = visualization.setup_plot(None)
plt.plot(xMofN, yMofN, '--', label='M of N')
plt.plot(xIPDA, yIPDA, label='IPDA')
ax.set_title('True detected tracks out of 500')
ax.set_xlabel('Scans needed')
ax.set_ylabel('Detected tracks')
ax.legend()
#ax.grid()
for axis in [ax.xaxis, ax.yaxis]:
    axis.set_major_locator(ticker.MaxNLocator(integer=True))
#plt.xlim([1, 20])
plt.ylim([0, 500])
plt.show()

