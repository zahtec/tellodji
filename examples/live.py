# Import Tello class from TelloDji
from tellodji import Tello

# Construct Tello class with verbose logging and automatic drone video stream turn on. Also automatically takeoff the dron
drone = Tello(debug=True, video=True, takeoff=True)

# Set the drones default speed to 60cm/s
drone.speed(60)

# Make drone go up 100cm
drone.up(100)

# Starts a live stream and automatically opens a new web browser tab with said live stream
drone.live()

# Lets do a cool sequence we can watch!
# Make the drone turn 180 deg clockwise
drone.clockwise(180)

# Make the drone flip right
drone.flip_right()

# Make the drone go backwards 20cm
drone.backward(20)

# Make the drone flip left
drone.flip_left()

# Make the drone go down 50cm
drone.down(50)

# Stop the live stream
drone.stop_live()

# Make the drone go backward 200cm
drone.backward(200)

# Land the drone
drone.land()

# Exit, can no longer use the class afterwards
drone.exit()
