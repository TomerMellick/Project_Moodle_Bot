# Orbit Moodle Bot #
This bot is an easy interface to Orbit's and Moodle's websites.

![GitHub release (latest by date including pre-releases)](https://img.shields.io/github/v/release/TomerMellick/Project_Moodle_Bot?include_prereleases)
![GitHub tag (latest SemVer pre-release)](https://img.shields.io/github/v/tag/TomerMellick/Project_Moodle_Bot?include_prereleases)  
![GitHub](https://img.shields.io/github/license/TomerMellick/Project_Moodle_Bot)

## How to Use ##
1. join the bot via [this link](https://t.me/moodle_hadassah_bot).
2. send to him your Orbit's username and password.
3. use any of its commands 

## How to Open Your Own Bot ##
1. Create bot via [BotFather](https://t.me/BotFather)
2. Download the code
3. Install the requirements packages with `pip install requirements.txt`
4. Copy the files in the `needed_files` dir to the `src` dir
5. Change the `BotToken.txt` to your token


## Requirements ##
1. python 3.9
2. all packages from `requirements.txt`

## Commands ##
start - start the telegram bot, wait for username and password  
update_user - update the user's info (ask again for username and password)  
get_grades - get all the grades of the student (include average grade)  
get_unfinished_events - get all unfinished events (from moodle)  
get_document - get document from the moodle  
update_schedule - update the schedule  
get_notebook - get notebook file  
get_upcoming_exams - get all upcoming exams  
grade_distribution - get distribution for specific grade  
change_password - change password in the orbit website  