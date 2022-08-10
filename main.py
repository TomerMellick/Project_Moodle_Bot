# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import requests

import re
import json

s = requests.Session()
r = s.get("https://live.or-bit.net/hadassah/Login.aspx")

ans = re.findall(r"<input type=\"hidden\" name=\"(.*?)\" id=\".*?\" value=\"(.*?)\" \/", r.text)
ans.append(("edtUsername", "{}"))
ans.append(("edtPassword", "{}"))
ans += [("__LASTFOCUS", ""), ("__EVENTTARGET", ""), ("__EVENTARGUMENT", ""), ("btnLogin", "כניסה")
        ]
ans = dict(ans)
r = s.post("https://live.or-bit.net/hadassah/Login.aspx", data=ans)
r = s.get("https://live.or-bit.net/hadassah/Handlers/Moodle.ashx")
ans = re.search("URL='(.*?)'", r.text)[1]
r = s.get(ans)
ans = re.search('"sesskey":"(.*?)"', r.text)[1]
string_url = f"https://mowgli.hac.ac.il/lib/ajax/service.php?sesskey={ans}&info=core_calendar_get_action_events_by_timesort"
r = s.post(string_url, json=[{"index": 0, "methodname": "core_calendar_get_action_events_by_timesort",
                              "args": {"limitnum": 6, "timesortfrom": 1658869200, "limittononsuspendedevents": True}}])
telegram_url = "https://api.telegram.org/bot{}/"
heb_txt = json.loads(r.text)
heb_txt = heb_txt[0]['event']['data']
id =
txt_string = heb_txt[0]['name']
txt_string = txt_string.replace('#', '%23%0A')
course_name =
s.get(f"{telegram_url}sendMessage?chat_id={id}&text={txt_string}")
