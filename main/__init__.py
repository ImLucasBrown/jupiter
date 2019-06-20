import logging
import time
import calendar
import datetime
import os
import urllib.request
from pprint import pprint

logger = logging.getLogger(__name__)
src = os.path.dirname(__file__)
api_key = open(os.path.join(src, "API_KEY.txt")).read()
n2yo_api_url = "https://www.n2yo.com/rest/v1/satellite/"

ABOVE = "above"
RADIO = "radio"
POSITION = "position"


class GroundStation:
    def __init__(self, lat, lng, alt, ignore=True):
        self.latitude = lat
        self.longitude = lng
        self.altitude = alt
        self.min_elevation = 12
        self.prediction_span = 1
        self.sat_id = -1
        self._mode = "above"
        self._category = 3
        self._data = dict()
        self._ignore_geo_stationary = ignore

    @property
    def ignore_geo_stationary(self):
        return self._ignore_geo_stationary

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, new_data):
        if isinstance(new_data, dict):
            if new_data.get(ABOVE) and self.ignore_geo_stationary:
                above_list = [d for d in new_data[ABOVE] if float(d['satalt']) < 34000.0]
                new_data[ABOVE] = above_list
                new_data['info']['satcount'] = len(above_list)
            self._data = new_data

    @property
    def category(self):
        return self._category

    @category.setter
    def category(self, category_id):
        self._category = category_id

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode_name):
        self._mode = mode_name

    def get_satellite_data(self, sat_id=None, position_time=1):
        if not api_key:
            return None
        if sat_id:
            sat_id = str(sat_id)
        else:
            sat_id = '0'
        self.sat_id = str(sat_id)
        position_time = str(position_time)
        lat = str(self.latitude)
        lng = str(self.longitude)
        alt = str(self.altitude)
        days = str(self.prediction_span)
        min_elevation = str(self.min_elevation)
        search_range = '85'
        category = str(self.category)
        request_url_radio = "/".join((n2yo_api_url, "radiopasses", sat_id, lat, lng, alt, days, min_elevation,
                                      "&apiKey=%s" % api_key))
        request_url_above = "/".join((n2yo_api_url, "above", lat, lng, alt, search_range, category,
                                      "&apiKey=%s" % api_key))
        request_url_positions = "/".join((n2yo_api_url, "positions", self.sat_id, lat, lng, alt,
                                          position_time, "&apiKey=%s" % api_key))
        request_url = request_url_radio
        if self.mode == ABOVE:
            request_url = request_url_above
        elif self.mode == POSITION:
            request_url = request_url_positions
        with urllib.request.urlopen(request_url) as response:
            data = eval(response.read())
            # pprint(data)
            self.data = data
            return self.data

    def find_transit(self):
        if self.mode == ABOVE:
            logger.warning("Can not calculate transits while in %s mode." % ABOVE)
            return
        if isinstance(self.data.get(ABOVE), list):
            if not len(self.data[ABOVE]):
                logger.warning("No satellites overhead.")
                return
            if not self.select_satellite():
                return
        for sat_pass in self.data['passes']:
            start_utc = sat_pass['startUTC']
            end_utc = sat_pass['endUTC']
            time_until_start = start_utc - current_utc()

            if current_utc() < start_utc and time_until_start <= 600:
                while current_utc() < start_utc:
                    time_until_start = start_utc - current_utc()
                    print(datetime.timedelta(seconds=time_until_start), "(Until pass)")
                    time.sleep(1)
                self.track_position(end_utc)
            elif current_utc() in range(start_utc, end_utc):
                print("Sat pass happening now! ID:%s" % self.sat_id)
                self.track_position(end_utc)

            else:
                print("Next pass wont be for a while: ", datetime.timedelta(seconds=time_until_start))

    def select_satellite(self):
        response = None
        sat_count = self.data['info']['satcount']
        pprint(self.data)
        while response != 'exit':
            if sat_count - 1 > 0:
                print("Select a satellite between 0 -", sat_count - 1)
                response = str(input())
                response = int(response)
            else:
                response = 0
            if response in range(0, sat_count):
                sat_dat = self.data[ABOVE][response]
                print(sat_dat)
                print("Select satellite y/n?")
                response = str(input())
                if response.lower() == "y":
                    self.mode = RADIO
                    self.get_satellite_data(sat_dat["satid"])
                    return True
            else:
                print("Invalid selection >>> %s" % response)
        return False

    def track_position(self, pass_end_time):
        '''
        Requests the position of a satellite for the duration of a transit. Updates are stored in a list.
        '''
        if self.sat_id >= 0:
            self.get_satellite_data(self.sat_id, position_time=pass_end_time - current_utc())
            for pos_data in self.data["positions"]:
                # TODO: Validate against timestamp
                azimuth = pos_data["azimuth"]
                elevation = pos_data["elevation"]
                time_until_end = pass_end_time - current_utc()
                print(datetime.timedelta(seconds=time_until_end), "a:%s | e:%s" % (azimuth, elevation))
                time.sleep(1)
            print("Pass has ended")


def current_utc():
    return calendar.timegm(time.gmtime())

