# Import Tello class from TelloDji
from tellodji import Tello

# Construct Tello class with verbose logging and automatic drone video stream turn on. Also set the default distance to 100cm
drone = Tello(debug = True, video = True, default_rotation = 180)

# Takeoff drone
drone.takeoff()

# Set the drones default speed to 60cm/s
drone.speed(60)

# Make drone go forward 100cm
drone.forward(100)

# Start video recording. Default saves to ./videos in mp4 format
drone.start_video()

# Lets do a cool sequence we can record!
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

# Stop the video
drone.stop_video()

# Start another video, this time in mov format
drone.start_video(path = './videos/video.mov')

# Lets do another cool sequence!
# Make the drone go up 50cm
drone.up(50)

# Make the drone go forward the default distance (50cm)
drone.forward()

# Stop the video
drone.stop_video()

# Land the drone
drone.land()

# Exit, can no longer use the class afterwards
drone.exit()
