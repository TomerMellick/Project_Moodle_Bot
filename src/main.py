import requests
import re
import json
import database
# getting the bot token from file
with open("BotToken.txt", "r") as BotToken_f:
    BotToken = BotToken_f.read()
telegram_url = f"https://api.telegram.org/bot{BotToken}/"

# getting the username and password from database
with open("DataBase.txt", "r") as DataBase_f:
    user_info = json.load(DataBase_f)

user_id =  #TODO getting from telegream
user_row = user_login(user_id)
user_name = user_row[1]
user_password = user_row[2]

# open session
s = requests.Session()

# GET orbit login page
orbit_session = s.get("https://live.or-bit.net/hadassah/Login.aspx")

# setting the POST headrs for the orbit login
login_POST_header = re.findall(r"<input type=\"hidden\" name=\"(.*?)\" id=\".*?\" value=\"(.*?)\" \/",
                               orbit_session.text)
login_POST_header.append((f"edtUsername", user_name))
login_POST_header.append((f"edtPassword", user_password))
login_POST_header += [("__LASTFOCUS", ""), ("__EVENTTARGET", ""), ("__EVENTARGUMENT", ""), ("btnLogin", "כניסה")]
login_POST_header = dict(login_POST_header)

# POST login to orbit
orbit_session = s.post("https://live.or-bit.net/hadassah/Login.aspx", data=login_POST_header)

# GET redirect to moodle
moodle_session = s.get("https://live.or-bit.net/hadassah/Handlers/Moodle.ashx")
redirect_url = re.search("URL='(.*?)'", moodle_session.text)[1]
moodle_session = s.get(redirect_url)

# POST to unfinished events
moodle_session_key = re.search('"sesskey":"(.*?)"', moodle_session.text)[1]
events_POST_url = f"https://mowgli.hac.ac.il/lib/ajax/service.php?sesskey={moodle_session_key}&info=core_calendar_get_action_events_by_timesort"
events_POST_headers = {"index": 0, "methodname": "core_calendar_get_action_events_by_timesort",
                              "args": {"limitnum": 6, "timesortfrom": 1658869200, "limittononsuspendedevents": True}}
unfinished_events = s.post(events_POST_url, json=[events_POST_headers])

# encoding the unicode response to hebrew
heb_txt = json.loads(unfinished_events.text)
heb_txt = heb_txt[0]['event']['data']

# building the message string
message_string = heb_txt[0]['name']
message_string = message_string.replace('#', '%23%0A')

# send telegram message
s.get(f"{telegram_url}sendMessage?chat_id={user_id}&text={message_string}")
