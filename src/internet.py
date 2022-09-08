from enum import Enum
from urllib.parse import urlencode, quote
from collections import namedtuple
from datetime import datetime
from typing import Union, List
import requests
import html
import json
import re

Grade = namedtuple('Grade', 'name units grade grade_distribution')
Exam = namedtuple('Exam', 'name number time_start time_end mark notebook_url room')
Event = namedtuple('event', 'name course_name course_id end_time url')
Res = namedtuple('Result', 'result warnings error')
GradesDistribution = namedtuple('GradesDistribution', 'grade average standard_deviation position image')


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
    __ORBIT_URL = 'https://live.or-bit.net/hadassah'
    __MAIN_URL = f'{__ORBIT_URL}/Main.aspx'
    __LOGIN_URL = f'{__ORBIT_URL}/Login.aspx'
    __CHANGE_PASSWORD_URL = f'{__ORBIT_URL}/ChangePassword.aspx'
    __CONNECT_MOODLE_URL = f'{__ORBIT_URL}/Handlers/Moodle.ashx'
    __GET_DOCUMENT_URL = f'{__ORBIT_URL}/DocumentGenerationPage.aspx'
    __GRADE_LIST_URL = f'{__ORBIT_URL}//StudentGradesList.aspx'
    __EXAMS_URL = f'{__ORBIT_URL}/StudentAssignmentTermList.aspx'

    __MOODLE_URL = 'https://mowgli.hac.ac.il/'
    __MY_MOODLE = f'{__MOODLE_URL}/my/'
    __MOODLE_SERVICE_URL = f'{__MOODLE_URL}/lib/ajax/service.php'

    def __init__(self, username: str, password: str):
        self.session = requests.session()
        self.moodle_res = Res(False, [], None)
        self.orbit_res = Res(False, [], None)
        self.username = username
        self.password = password

    class Error(Enum):
        ORBIT_DOWN = 0
        MOODLE_DOWN = 1
        WRONG_PASSWORD = 2
        BOT_ERROR = 3
        WEBSITE_DOWN = 4
        CHANGE_PASSWORD = 5
        OLD_EQUAL_NEW_PASSWORD = 6

    class Warning(Enum):
        CHANGE_PASSWORD = 0

    def connect_orbit(self) -> Res:
        """
        connect to robit website using the username and password
        if this object already connected the method do nothing (and return the res of the first time tried to connect)
        :return: is the method successfully connect to orbit
        """
        if self.orbit_res.result:
            return self.orbit_res

        orbit_login_website = self.__get(Internet.__LOGIN_URL)

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
        orbit_website = self.__post(Internet.__LOGIN_URL, payload_data=login_data)

        if orbit_website.status_code != 200 or orbit_website.url == Internet.__LOGIN_URL:
            self.orbit_res = Res(False, [], Internet.Error.WRONG_PASSWORD)
            return self.orbit_res

        if orbit_website.url == Internet.__CHANGE_PASSWORD_URL:
            if self.__get(Internet.__MAIN_URL).url == Internet.__CHANGE_PASSWORD_URL:
                self.orbit_res = Res(False, [], Internet.Error.CHANGE_PASSWORD)
                return self.orbit_res
            self.orbit_res.warnings.append(Internet.Warning.CHANGE_PASSWORD)

        self.orbit_res = Res(True, self.orbit_res.warnings, None)
        return self.orbit_res

    def connect_moodle(self) -> Res:
        """
        connect to moodle website
        :return: is the method successfully connect to moodle
        """
        if self.moodle_res.result:
            return self.moodle_res

        res, warnings, error = self.connect_orbit()

        warnings = warnings[:]

        if not res:
            self.moodle_res = Res(False, warnings, error)
            return self.moodle_res

        moodle_session = self.__get(Internet.__CONNECT_MOODLE_URL)
        if moodle_session.status_code != 200:
            self.moodle_res = Res(False, warnings, Internet.Error.MOODLE_DOWN)
            return self.moodle_res

        reg = re.search("URL='(.*?)'", moodle_session.text)
        if not reg:
            self.moodle_res = Res(False, warnings, Internet.Error.BOT_ERROR)

        redirect_url = reg[1]
        moodle_website = self.__get(redirect_url)
        if moodle_website.status_code != 200 or moodle_website.url != Internet.__MY_MOODLE:
            self.moodle_res = Res(False, warnings, Internet.Error.MOODLE_DOWN)
            return self.moodle_res
        self.moodle_res = Res(True, warnings, None)
        return self.moodle_res

    def get_unfinished_events(self, last_date: datetime = None) -> Res:
        """
        get undefined events from the moodle website

        :param: last_date: events that past that date filtered out of the of
        :return: the last undefined events or None if something go wrong
        """
        res, warnings, error = self.connect_moodle()

        warnings = warnings[:]

        if not res:
            return Res(None, warnings, error)

        moodle_website = self.__get(Internet.__MY_MOODLE)

        if moodle_website.status_code != 200:
            return Res(None, warnings, Internet.Error.MOODLE_DOWN)

        reg = re.search('"sesskey":"(.*?)"', moodle_website.text)
        if not reg:
            return Res(None, warnings, Internet.Error.BOT_ERROR)

        moodle_session_key = reg[1]

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
        unfinished_events = self.__post(Internet.__MOODLE_SERVICE_URL,
                                        payload_json=post_payload,
                                        get_payload=get_payload)
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

    def get_document(self, document: Document) -> Res:
        """
        get specific document from the moodle website
        :param document: the document needed from the orbit website
        :return: a raw data of the document (bytes)
        """
        res, warnings, error = self.connect_orbit()
        if not res:
            return Res(False, warnings, error)

        website = self.__get(Internet.__GET_DOCUMENT_URL)
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)
        hidden_inputs = self.__get_hidden_inputs(website.text)
        hidden_inputs['ctl00$ContentPlaceHolder1$cmbDivision'] = 1
        hidden_inputs[f'ctl00$ContentPlaceHolder1$gvDocuments$GridRow{document.value}$ibDownloadDocument.x'] = 1
        hidden_inputs[f'ctl00$ContentPlaceHolder1$gvDocuments$GridRow{document.value}$ibDownloadDocument.y'] = 1
        print(hidden_inputs)
        return Res(self.__post('Internet.__GET_DOCUMENT_URL',
                               payload_data=hidden_inputs).content, warnings, None)

    def get_grades(self) -> Res:
        """
        get all orbits grades and connect the orbit with username and password if not connected yet
        :return: list of Grades: the grades of the user
        """
        res, warnings, error = self.connect_orbit()
        if not res:
            return Res(False, warnings, error)

        website = self.__get(Internet.__GRADE_LIST_URL)
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)

        pages_regex = 'javascript:__doPostBack\\(&#39;ctl00\\' \
                      '$ContentPlaceHolder1\\$gvGradesList&#39;,&#39;Page\\$([1-9])&#39;\\)'
        last_page = len(re.findall(pages_regex, website.text)) + 1
        page = 1
        grades = []
        while page <= last_page:
            grades += Internet.__get_grade_from_page(website.text, page)
            page += 1
            if page <= last_page:
                inputs = Internet.__get_hidden_inputs(website.text)
                inputs['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$gvGradesList'
                inputs['__EVENTARGUMENT'] = f'Page${page}'
                website = self.__post(Internet.__GRADE_LIST_URL, payload_data=inputs)

        return Res(grades, warnings, None)

    def __get_exam_website(self) -> Res:
        """
        get the website of the exams from the orbit
        :return: Respond of the website
        """
        res, warnings, error = self.connect_orbit()
        if not res:
            return Res(False, warnings, error)
        website = self.__get(Internet.__EXAMS_URL)
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)
        return Res(website, warnings, None)

    def get_all_exams(self) -> Res:
        """
        get list of the user's exams
        :return: list of the user's exams
        """
        website, warnings, error = self.__get_exam_website()
        if not website:
            return Res(website, warnings, error)
        inputs = Internet.__get_hidden_inputs(website.text)
        inputs['ctl00$tbMain$ctl03$ddlExamDateRangeFilter'] = 1
        website = self.__post(Internet.__EXAMS_URL, payload_data=inputs)
        all_exams_text = re.findall(
            '<tr id="ContentPlaceHolder1_gvStudentAssignmentTermList" class="GridRow">(?:.*?)*</tr>',
            website.text,
            re.DOTALL)
        all_exams_text = [re.findall('<td.*?>(.*?)</td>', exam, re.DOTALL) for exam in all_exams_text]

        all_exams = []
        for exam in all_exams_text:
            name = exam[10]
            time = re.search('>([^>]*?)</span', exam[2]).group(1).split('-')
            if len(time) < 2:
                time = ['00:00', '00:00']
            if exam[0] == '&nbsp;':
                exam[0] = '01/01/0001'
            time_start = datetime.strptime(f"{exam[0]} {time[0]}", '%d/%m/%Y %H:%M')
            time_end = datetime.strptime(f"{exam[0]} {time[1]}", '%d/%m/%Y %H:%M')
            number = exam[4]
            mark = None if exam[5] == '&nbsp;' else exam[5]
            room = '' if exam[7] == '&nbsp;' else exam[7]
            notebook = re.search(
                r'ctl00\$ContentPlaceHolder1\$gvStudentAssignmentTermList\$GridRow([0-9]*)\$btnDownload', exam[13])
            if notebook:
                notebook = notebook.group(1)
            all_exams.append(Exam(name=name,
                                  number=number,
                                  time_start=time_start,
                                  time_end=time_end,
                                  mark=mark,
                                  notebook_url=notebook,
                                  room=room))

        return Res(all_exams, warnings, None)

    def get_exam_notebook(self, number):
        """
        get notebook of specific exam
        :param number: the number of the notebook (Exam.notebook_url)
        :return: a row data of the file
        """
        website, warnings, error = self.__get_exam_website()
        if not website:
            return Res(website, warnings, error)
        inputs = Internet.__get_hidden_inputs(website.text)
        inputs['ctl00$btnOkAgreement'] = 'אישור'
        inputs['ctl00$tbMain$ctl03$ddlExamDateRangeFilter'] = 1
        website = self.__post(Internet.__EXAMS_URL, payload_data=inputs)
        inputs = Internet.__get_hidden_inputs(website.text)
        inputs['ctl00$tbMain$ctl03$ddlExamDateRangeFilter'] = 1
        inputs[f'ctl00$ContentPlaceHolder1$gvStudentAssignmentTermList$GridRow{number}$btnDownload.x'] = 1
        inputs[f'ctl00$ContentPlaceHolder1$gvStudentAssignmentTermList$GridRow{number}$btnDownload.y'] = 1
        return Res(self.__post(Internet.__EXAMS_URL,
                               payload_data=inputs).content, warnings, None)

    def change_password(self, new_password: str):
        """
        change password in the orbit website
        :param new_password: the new password the user want
        :return: is the password changed successfully
        """
        if self.password == new_password:
            return Res(False, [], Internet.Error.OLD_EQUAL_NEW_PASSWORD)
        res, warnings, error = self.connect_orbit()
        if not res and error != Internet.Error.CHANGE_PASSWORD:
            return Res(False, warnings, error)
        website = self.__get(Internet.__CHANGE_PASSWORD_URL)
        inputs = Internet.__get_hidden_inputs(website.text)
        inputs['ctl00$ContentPlaceHolder1$edtCurrentPassword'] = self.password
        inputs['ctl00$ContentPlaceHolder1$edtNewPassword1'] = new_password
        inputs['ctl00$ContentPlaceHolder1$edtNewPassword2'] = new_password
        inputs['ctl00$ContentPlaceHolder1$btnSave'] = 'עדכן'
        website = self.__post(Internet.__CHANGE_PASSWORD_URL, payload_data=inputs)
        if 'OLScriptCounter1alert() { window.alert(' in website.text:
            return Res(False, [], Internet.Error.OLD_EQUAL_NEW_PASSWORD)
        return Res(True, [], None)

    def get_grade_distribution(self, grade_distribution: str):
        """
        get the grade distribution of specific subject
        :param grade_distribution: the Grade.grade_distribution of the wanted subject
        :return: GradesDistribution
        """
        res, warnings, error = self.connect_orbit()
        if not res:
            return Res(False, warnings, error)

        website = self.__get(Internet.__GRADE_LIST_URL)
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)
        grade_distribution = grade_distribution.split('_')

        inputs = Internet.__get_hidden_inputs(website.text)
        inputs['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$gvGradesList'
        inputs['__EVENTARGUMENT'] = f'Page${grade_distribution[0]}'
        website = self.__post(Internet.__GRADE_LIST_URL, payload_data=inputs)
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)

        inputs = Internet.__get_hidden_inputs(website.text)
        inputs[f'ctl00'
               f'$ContentPlaceHolder1'
               f'$gvGradesList'
               f'$GridRow{grade_distribution[1]}'
               f'$imgShowGradeDistribution.x'] = 1
        inputs[f'ctl00'
               f'$ContentPlaceHolder1'
               f'$gvGradesList'
               f'$GridRow{grade_distribution[1]}'
               f'$imgShowGradeDistribution.y'] = 1
        website = self.__post(Internet.__GRADE_LIST_URL, payload_data=inputs)
        if website.status_code != 200:
            return Res(False, warnings, Internet.Error.BOT_ERROR)
        table = re.findall('<span id="ContentPlaceHolder1_ucLessonGradeDistribution_lblStatData"><table>(.*?)</table>',
                           website.text, re.DOTALL)[0]
        table = re.findall('<td.*?>(.*?)</td>', table, re.DOTALL)
        grade = table[1]
        avg = table[3]
        standard_deviation = table[5]
        position = table[7]
        img_url = re.findall('src="(/hadassah/ChartImg.axd\\?.*?)"', website.text, re.DOTALL)[0]
        img_website = self.__get(f'https://live.or-bit.net{img_url}')
        img = img_website.content
        return Res(
            GradesDistribution(
                grade=grade,
                average=avg,
                standard_deviation=standard_deviation,
                position=position,
                image=img
            ),
            warnings=warnings,
            error=None
        )

    @staticmethod
    def __get_grade_from_page(page: str, page_number: int) -> List[Grade]:
        """
        get grades from specific page
        :param page: the page data (HTML code)
        :param page_number: the page number
        :return: a list of all Grades in the page
        """
        subjects_str = re.findall('<tr id="ContentPlaceHolder1_gvGradesList" class="GridRow">(.*?)</tr>',
                                  page,
                                  re.DOTALL)
        final_res = []
        for subject in subjects_str:
            data = re.findall('<td.*?>(.*?)</td>', subject, re.DOTALL)
            grade_distribution = re.search(
                r'ctl00\$ContentPlaceHolder1\$gvGradesList\$GridRow([0-9]+?)\$imgShowGradeDistribution', data[6])
            if grade_distribution:
                grade_distribution = f'{page_number}_{grade_distribution.group(1)}'
            final_res.append(
                Grade(
                    name=html.unescape(data[1]),
                    units=int(data[4]),
                    grade=re.findall('>(.*?)</span>', data[6])[0],
                    grade_distribution=grade_distribution
                )
            )
        return final_res

    def __get(self, url: str, payload: dict = None) -> requests.Response:
        """
        use the get function of the session
        :param url: the url to go to
        :param payload: the payload (the data that come after the ? in the url)
        :return: the Response of the session
        """
        if payload is not None:
            payload = '&' + urlencode(payload, quote_via=quote)
        else:
            payload = ''
        return self.session.get(f"{url}{payload}")

    def __post(self, url: str,
               payload_data: dict = None,
               payload_json: Union[dict, list] = None,
               get_payload: dict = None) -> requests.Response:
        """
        use the post function of the session
        :param url: the url to go to
        :param payload_data: same as in the `session.post` parameter
        :param payload_json: same as in the `session.post` parameter
        :param get_payload: the get payload (the data that come after the ? in the url)
        :return: the Response of the session
        """

        if get_payload is not None:
            get_payload = '?' + urlencode(get_payload, quote_via=quote)
        else:
            get_payload = ''
        return self.session.post(f"{url}{get_payload}", data=payload_data, json=payload_json)

    @staticmethod
    def __get_hidden_inputs(text: str) -> dict:
        """
        get all hidden inputs from the website (include the year)
        :param text: the html code
        :return: dict with all the hidden inputs and their values
        """
        hidden_input_regex = r"<input type=\"hidden\" name=\"(.*?)\" id=\".*?\" value=\"(.*?)\" \/>"
        hidden_inputs = re.findall(hidden_input_regex, text, re.DOTALL)
        year_regex = '<select name="ctl00\\$cmbActiveYear".*?<option selected="selected" value="([0-9]*?)"'
        year = re.findall(year_regex, text, re.DOTALL)
        if year:
            year = int(year[0])
            hidden_inputs.append(('ctl00$cmbActiveYear', year))
        return dict(hidden_inputs)
