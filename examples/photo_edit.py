# Import Pillow (https://pillow.readthedocs.io/en/stable/) and TelloDji
from PIL.ImageFilter import BLUR
from PIL.Image import open
from tellodji import Tello
from io import BytesIO

# Construct Tello class with verbose logging and automatic drone video stream turn on. Also with automatic takeoff
drone = Tello(('127.0.0.1', None), debug=True, video=True, takeoff=True)

# Make the drone go up 30cm
drone.up(30)

# Take a photo using the drone and return the bytes of said photo
# Then create a BytesIO class out of it for pillow to understand
# Then using pillow open it in a new image object
image = open(BytesIO(drone.photo_bytes()))

# Blur the image
image.filter(BLUR)

# Save this photo as photo.png in the current directory
image.save('./photo.png')

# Exit, can no longer use the class afterwards
drone.exit()
