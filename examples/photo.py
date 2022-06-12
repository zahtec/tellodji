# Import Tello class from TelloDji
from tellodji import Tello

# Construct Tello class with verbose logging and automatic drone video stream turn on. Also set the default distance to 100cm
drone = Tello(debug = True, video = True, default_distance = 100)

# Takeoff drone
drone.takeoff()

# Make drone go up default distance (100cm)
drone.up()

# Make drone go forward 100cm
drone.forward(100)

# Make drone turn default rotation counter-clockwise (90deg)
drone.counter_clockwise()

# Snap a photo! Default saves to ./photos in png format
drone.photo()

# Make the drone turn 180 deg clockwise
drone.clockwise(180)

# Takes a photo into the directory ./other_photos in 480p (Using the class constant SD). Then displays in the default image viewing program on your platform
drone.photo(path = './other_photos/', resolution = Tello.SD, window = True)

# Land the drone
drone.land()

# Exit, can no longer use the class afterwards
drone.exit()
