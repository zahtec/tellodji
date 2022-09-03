# Import Tello class from TelloDji
from tellodji import Tello

# Construct Tello class with verbose logging and mission pads enabled. With auto takeoff
drone = Tello(debug=True, mission_pad=True, takeoff=True)

# Get the current main mission pad ID and print it
print(drone.get_mission_pad())

# Make the drone jump from 80 y at the center of mission pad 1 to mission pad 2 and rotate its yaw to 20 deg at the default speed (50 cm/s)
# Class constants (Tello.M1, etc...) can be used but strings ('m1', etc...) can also be used
drone.jump(0, 80, 0, Tello.M1, Tello.M2, 20)

# get current acceleration of the z axis
print(drone.get_az())

# Disable mission pads
drone.mission_pad(False)

# Land the drone
drone.land()

# Exit, can no longer use the class afterwards
drone.exit()
