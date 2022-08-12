from urllib.parse import urlencode, quote
from collections import namedtuple
from datetime import datetime
from typing import Union, List
import requests
import html
import json
import re

Grade = namedtuple('Grade', 'name units grade')


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

        login_data = Internet.__get_hidden_inputs(orbit_login_website.text)
        login_data.update(
            {
                'edtUsername': username,
                'edtPassword': password,
                '__LASTFOCUS': '',
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                'btnLogin': 'כניסה'
            }
        )
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

    def get_grades(self, username: str = None, password: str = None) -> Union[List[Grade], None]:
        """
        get all orbits grades and connect the orbit with username and password if not connected yet
        :param username: orbit username (may be None if already connected)
        :param password: orbit password (may be None if already connected)
        :return: the grades of the user
        """
        if not self.connect_orbit(username, password):
            return None
        website = self.__get('https://live.or-bit.net/hadassah/StudentGradesList.aspx')
        if website.status_code != 200:
            return None

        pages_regex = 'javascript:__doPostBack\\(&#39;ctl00\\' \
                      '$ContentPlaceHolder1\\$gvGradesList&#39;,&#39;Page\\$([1-9])&#39;\\)'
        last_page = len(re.findall(pages_regex, website.text)) + 1
        page = 1
        grades = []
        while page <= last_page:
            grades += Internet.__get_grade_from_page(website.text)
            page += 1
            if page <= last_page:
                inputs = Internet.__get_hidden_inputs(website.text)
                inputs['ctl00$cmbActiveYear'] = '2022'
                inputs['__EVENTARGUMENT'] = f'Page${page}'
                inputs['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$gvGradesList'
                print(inputs)
                website = self.__post('https://live.or-bit.net/hadassah/StudentGradesList.aspx',payload_data=inputs)
        return grades

    @staticmethod
    def __get_grade_from_page(page: str) -> List[Grade]:
        subjects_str = re.findall('<tr id="ContentPlaceHolder1_gvGradesList" class="GridRow">(.*?)</tr>',
                                  page,
                                  re.DOTALL)
        final_res = []
        for subject in subjects_str:
            data = re.findall('<td.*?>(.*?)</td>', subject, re.DOTALL)
            final_res.append(
                Grade(
                    name=html.unescape(data[1]),
                    units=int(data[4]),
                    grade=re.findall('>([0-9א-ת]*?)</span>', data[6])[0])
            )
        return final_res

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

    @staticmethod
    def __get_hidden_inputs(text: str) -> dict:
        hidden_input_regex = r"<input type=\"hidden\" name=\"(.*?)\" id=\".*?\" value=\"(.*?)\" \/>"
        return dict(re.findall(hidden_input_regex, text))
