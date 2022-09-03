# Import Tello class from TelloDji
from tellodji import Tello

# Construct Tello class with verbose logging and automatic takeoff
drone = Tello(debug=True, takeoff=True)

# Get battery level and print it
print(drone.get_battery())

# Make drone go up 100cm
drone.up(100)

# Define a callback function for the next few methods
def callback(res):
    print(res)

# Set default callback function so we don't have to repeat ourselves
drone.set_sync(callback)

# When running asynchronously like so, chaining methods is possible
# Make the drone flip right
# Make the drone go forward 30cm
# Make the drone flip left
# Make the drone turn counter-clockwise 180 deg
# Make the drone go forward 30cm again
# Land the drone
drone.flip_right().forward(30).flip_left().counter_clockwise(180).forward(30).land()

# Make the drone takeoff again to 80cm (80cm is the default set by the SDK)
drone.takeoff()

# Make the drone move up 50 y (first 130 is the y cordnate)
# Then curve to 100 x and 80 z at 50cm/s
drone.curve(0, 130, 0, 100, 130, 80, 50)

# Go back to synchronous mode
drone.set_sync(False)

# Land the drone
drone.land()

# Exit, can no longer use the class afterwards
drone.exit()
