import main
import os

src = os.path.dirname(__file__)

# sat_id = 25338  # NOAA 15
# sat_id = 28654  # NOAA 18
# sat_id = 33591  # NOAA 19

# Create a text file with latitude, longitude, and approximate elevation separated by commas.
lat, lng, alt = open(os.path.join(src, "me.txt")).read().split(',')

ground = main.GroundStation(lat, lng, alt)
ground.get_satellite_data()
ground.mode = main.RADIO
ground.transit()
