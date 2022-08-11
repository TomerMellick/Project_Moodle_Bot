from typing import Union
from urllib.parse import urlencode, quote
from datetime import datetime
import requests
import json
import re


class Internet:
    """
    This class communicate with orbit and moodle.
    """
    def __init__(self):
        self.session = requests.session()
        self.moodle = False
        self.orbit = False

    def connect_orbit(self, username: str, password: str) -> bool:
        """
        connect to orbit (this is the required to connect the moodle)
        if this object already connected the method do nothing (and return True)

        :param username: orbit username (id number)
        :param password: orbit password
        :return: is the method successfully connect to orbit
        """
        if self.orbit:
            return True

        orbit_login_website = self.__get('https://live.or-bit.net/hadassah/Login.aspx')

        if orbit_login_website.status_code != 200:
            return False

        hidden_input_regex = r"<input type=\"hidden\" name=\"(.*?)\" id=\".*?\" value=\"(.*?)\" \/>"
        login_data = dict(re.findall(hidden_input_regex, orbit_login_website.text))
        login_data['edtUsername'] = username
        login_data['edtPassword'] = password
        login_data['__LASTFOCUS'] = ''
        login_data['__EVENTTARGET'] = ''
        login_data['__EVENTARGUMENT'] = ''
        login_data['btnLogin'] = 'כניסה'

        orbit_website = self.__post('https://live.or-bit.net/hadassah/Login.aspx', payload_data=login_data)

        if orbit_website.status_code != 200:
            return False
        self.orbit = True
        return True

    def connect_moodle(self, username: str = None, password: str = None) -> bool:
        """
        connect to moodle
        if this object already connected the method do nothing (and return True)
        if this object didnt connect to the orbit yet, connect with the username and password to the orbit

        :param username: orbit username (id number)
        :param password: orbit password
        :return: is the method successfully connect to moodle
        """
        if self.moodle:
            return True
        if not self.connect_orbit(username, password):
            return False
        moodle_session = self.__get("https://live.or-bit.net/hadassah/Handlers/Moodle.ashx")
        redirect_url = re.search("URL='(.*?)'", moodle_session.text)[1]
        if self.__get(redirect_url).status_code != 200:
            return False
        self.moodle = True
        return True

    def get_unfinished_events(self, username: str = None, password: str = None):
        """
        get undefined events
        if this object didnt connect to the orbit yet, connect with the username and password to the orbit
        if this object didnt connect to the moodle yet, connect to the moodle

        :param username: orbit username (id number) (optional if not connected to orbit)
        :param password: orbit password (optional if not connected to orbit)
        :return: the last undefined events or None if something go wrong
        """
        if not self.connect_moodle(username, password):
            return False

        moodle_website = self.__get('https://mowgli.hac.ac.il/my/')

        if moodle_website.status_code != 200:
            return False

        moodle_session_key = re.search('"sesskey":"(.*?)"', moodle_website.text)[1]

        url = 'https://mowgli.hac.ac.il/lib/ajax/service.php'
        get_payload = {'sesskey': moodle_session_key,
                       'info': 'core_calendar_get_action_events_by_timesort'}
        post_payload = [{"index": 0,
                         "methodname": "core_calendar_get_action_events_by_timesort",
                         "args": {
                             "limitnum": 50,
                             "timesortfrom": int(datetime.now().timestamp()),
                             "limittononsuspendedevents": True
                         }
                         }]
        unfinished_events = self.__post(url, payload_json=post_payload, get_payload=get_payload)
        if unfinished_events.status_code != 200:
            return False
        data = json.loads(unfinished_events.text)
        if data[0]['error']:
            return False

        return data[0]['data']['events']

    def __get(self, url: str, payload: dict = None) -> requests.Response:
        if payload is not None:
            payload = '&' + urlencode(payload, quote_via=quote)
        else:
            payload = ''
        return self.session.get(f"{url}{payload}")

    def __post(self, url: str,
               payload_data: dict = None,
               payload_json: Union[dict, list] = None,
               get_payload: dict = None) -> requests.Response:
        if get_payload is not None:
            get_payload = '?' + urlencode(get_payload, quote_via=quote)
        else:
            get_payload = ''
        return self.session.post(f"{url}{get_payload}", data=payload_data, json=payload_json)
