from enum import Enum, auto
from urllib.parse import urlencode, quote
from collections import namedtuple
from datetime import datetime
from typing import Union, List
import requests
import html
import json
import re

Grade = namedtuple('Grade', 'name units grade')
Event = namedtuple('event', 'name course_name course_id end_time url')
Res = namedtuple('Result', 'result warnings error')


class Document(Enum):
    STUDENT_PERMIT_E = 0
    STUDENT_PERMIT = 1
    TUITION_FEE_APPROVAL = 2
    REGISTRATION_CONFIRMATION = 3
    GRADES_SHEET_E = 4
    GRADES_SHEET = 5
    ENGLISH_LEVEL = 13


documents_heb_name = {
    Document.STUDENT_PERMIT_E: 'v12 אישור לימודים באנגלית לסטודנט',
    Document.STUDENT_PERMIT: 'V45- אישור לימודים מפורט',
    Document.TUITION_FEE_APPROVAL: 'אישור גובה שכר לימוד',
    Document.REGISTRATION_CONFIRMATION: 'אישור הרשמה',
    Document.GRADES_SHEET_E: 'גליון ציונים באנגלית',
    Document.GRADES_SHEET: 'גליון ציונים',
    Document.ENGLISH_LEVEL: 'רמת אנגלית'
}
documents_file_name = {
    Document.STUDENT_PERMIT_E: 'student_permit_english.pdf',
    Document.STUDENT_PERMIT: 'student_permit.pdf',
    Document.TUITION_FEE_APPROVAL: 'tuition_fee_approval.pdf',
    Document.REGISTRATION_CONFIRMATION: 'registration_confirmation.pdf',
    Document.GRADES_SHEET_E: 'english_grades_sheet.pdf',
    Document.GRADES_SHEET: 'grades_sheet.pdf',
    Document.ENGLISH_LEVEL: 'english_level.pdf'
}


class Internet:
    """
    This class communicate with orbit and moodle.
    """

    def __init__(self, username: str, password: str):
        self.session = requests.session()
        self.moodle_res = Res(False, [], None)
        self.orbit_res = Res(False, [], None)
        self.username = username
        self.password = password

    class Error(Enum):
        ORBIT_DOWN = 0b001
        MOODLE_DOWN = 0b010
        WRONG_PASSWORD = 0b100
        BOT_ERROR = 0b1000
        WEBSITE_DOWN = ORBIT_DOWN | MOODLE_DOWN

    class Warning(Enum):
        CHANGE_PASSWORD = auto()

    def connect_orbit(self) -> Res:
        """
        connect to orbit (this is the required to connect the moodle)
        if this object already connected the method do nothing (and return True)

        :return: is the method successfully connect to orbit
        """
        if self.orbit_res.result:
            return self.orbit_res

        orbit_login_website = self.__get('https://live.or-bit.net/hadassah/Login.aspx')

        if orbit_login_website.status_code != 200:
            self.orbit_res = Res(False, [], Internet.Error.ORBIT_DOWN)
            return self.orbit_res

        login_data = Internet.__get_hidden_inputs(orbit_login_website.text)
        login_data.update(
            {
                'edtUsername': self.username,
                'edtPassword': self.password,
                '__LASTFOCUS': '',
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                'btnLogin': 'כניסה'
            }
        )
        orbit_website = self.__post('https://live.or-bit.net/hadassah/Login.aspx', payload_data=login_data)

        if orbit_website.status_code != 200 or orbit_website.url == 'https://live.or-bit.net/hadassah/Login.aspx':
            self.orbit_res = Res(False, [], Internet.Error.WRONG_PASSWORD)
            return self.orbit_res

        if orbit_website.url == 'https://live.or-bit.net/hadassah/ChangePassword.aspx':
            self.orbit_res.warnings.append(Internet.Warning.CHANGE_PASSWORD)

        self.orbit_res = Res(True, self.orbit_res.warnings, None)
        return self.orbit_res

    def connect_moodle(self) -> Res:
        """
        connect to moodle
        if this object already connected the method do nothing (and return True)
        if this object didnt connect to the orbit yet, connect with the username and password to the orbit

        :return: is the method successfully connect to moodle
        """
        if self.moodle_res.result:
            return self.moodle_res

        res, warnings, error = self.connect_orbit()

        warnings = warnings[:]

        if not res:
            self.moodle_res = Res(False, warnings, error)
            return self.moodle_res

        moodle_session = self.__get("https://live.or-bit.net/hadassah/Handlers/Moodle.ashx")
        if moodle_session.status_code != 200:
            self.moodle_res = Res(False, warnings, Internet.Error.MOODLE_DOWN)
            return self.moodle_res

        reg = re.search("URL='(.*?)'", moodle_session.text)
        if not reg:
            self.moodle_res = Res(False, warnings, Internet.Error.BOT_ERROR)

        redirect_url = reg[1]
        moodle_website = self.__get(redirect_url)
        if moodle_website.status_code != 200 or moodle_website.url != 'https://mowgli.hac.ac.il/my/':
            self.moodle_res = Res(False, warnings, Internet.Error.MOODLE_DOWN)
            return self.moodle_res
        self.moodle_res = Res(True, warnings, None)
        return self.moodle_res

    def get_unfinished_events(self, last_date: datetime = None) -> Res:
        """
        get undefined events
        if this object didnt connect to the orbit yet, connect with the username and password to the orbit
        if this object didnt connect to the moodle yet, connect to the moodle

        :return: the last undefined events or None if something go wrong
        """
        res, warnings, error = self.connect_moodle()

        warnings = warnings[:]

        if not res:
            return Res(None, warnings, error)

        moodle_website = self.__get('https://mowgli.hac.ac.il/my/')

        if moodle_website.status_code != 200:
            return Res(None, warnings, Internet.Error.MOODLE_DOWN)

        reg = re.search('"sesskey":"(.*?)"', moodle_website.text)
        if not reg:
            return Res(None, warnings, Internet.Error.BOT_ERROR)

        moodle_session_key = reg[1]

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
            return Res(None, warnings, Internet.Error.BOT_ERROR)
        data = json.loads(unfinished_events.text)
        if data[0]['error']:
            return Res(None, warnings, Internet.Error.BOT_ERROR)
        data = [Event(name=event['name'],
                      course_name=event['course']['shortname'],
                      course_id=event['course']['id'],
                      end_time=datetime.fromtimestamp(event['timesort']),
                      url=event['url'])
                for event in data[0]['data']['events']
                ]
        if last_date:
            data = list(filter(lambda event: event.end_time <= last_date, data))
        return Res(data, warnings, None)

    def get_document(self, document: Document):
        res, warnings, error = self.connect_orbit()
        if not res:
            return Res(False, warnings, error)

        website = self.__get('https://live.or-bit.net/hadassah/DocumentGenerationPage.aspx')
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)
        hidden_inputs = self.__get_hidden_inputs(website.text)
        hidden_inputs['ctl00$ContentPlaceHolder1$cmbDivision'] = 1
        hidden_inputs[f'ctl00$ContentPlaceHolder1$gvDocuments$GridRow{document.value}$ibDownloadDocument.x'] = 1
        hidden_inputs[f'ctl00$ContentPlaceHolder1$gvDocuments$GridRow{document.value}$ibDownloadDocument.y'] = 1

        return self.__post('https://live.or-bit.net/hadassah/DocumentGenerationPage.aspx',
                           payload_data=hidden_inputs).content

    def get_grades(self) -> Res:
        """
        get all orbits grades and connect the orbit with username and password if not connected yet
        :return: the grades of the user
        """
        res, warnings, error = self.connect_orbit()
        if not res:
            return Res(False, warnings, error)

        website = self.__get('https://live.or-bit.net/hadassah/StudentGradesList.aspx')
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)

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
                inputs['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$gvGradesList'
                inputs['__EVENTARGUMENT'] = f'Page${page}'
                website = self.__post('https://live.or-bit.net/hadassah/StudentGradesList.aspx', payload_data=inputs)

        return Res(grades, warnings, None)

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
        hidden_inputs = re.findall(hidden_input_regex, text)
        year_regex = '<select name="ctl00$cmbActiveYear".*?<option selected="selected" value="([0-9]*?)"'
        year = re.findall(year_regex, text)
        if year:
            year = year[0]
            hidden_inputs.append(('ctl00$cmbActiveYear', year))
        return dict(hidden_inputs)
