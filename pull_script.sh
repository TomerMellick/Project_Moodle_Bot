cd ~/bot_develop/Project_Moodle_Bot/src

pkill -f bot_develop

git checkout master

git pull

bash -c "exec -a bot_develop python main.py &"