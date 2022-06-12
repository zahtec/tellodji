# Import Tello class from TelloDji
from tellodji import Tello

# Construct Tello class with verbose logging
drone = Tello(debug = True)

# Get battery level and print it
print(drone.get_battery())

# Takeoff drone
drone.takeoff()

# Make drone go up 100cm
drone.up(100)

# Make drone go forward 800cm
drone.forward(800)

# Define a callback function for the next few methods
def callback(res):
    print(res)

# Set default callback function so we don't have to repeat ourselves
drone.set_sync(callback)

# When running asynchronously like so, chaining methods is possible
# Make the drone turn clockwise 90 deg
# Make the drone go forward the default distance set (in this case 50cm since that's the default)
# Make the drone go down 30cm
drone.clockwise(90).forward().down(30)

# Land the drone
drone.land()

# Exit, can no longer use the class afterwards
drone.exit()
