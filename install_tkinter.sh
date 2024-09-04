#!/bin/bash

sudo apt update
sudo apt install -y fswebcam python3 python3-tk python3-pip guvcview
sudo git clone https://github.com/cj-plusplus/LoginTracker /usr/local/bin/LoginTracker
sudo chmod -R a+rw /usr/local/bin/LoginTracker

touch /usr/local/bin/LoginTracker/spreadsheet_url.txt

echo "creating venv..."
python3 -m venv /usr/local/bin/LoginTracker/.venv
source /usr/local/bin/LoginTracker/.venv/bin/activate
pip install gspread
pip install opencv-python

#set up autolaunch then launch the program
echo -e "[Desktop Entry]\nName=LoggyTracker\nExec=/usr/local/bin/LoginTracker/.venv/bin/python3 /usr/local/bin/LoginTracker/main_tkinter.py" | sudo tee /etc/xdg/autostart/LoggyTracker.desktop
echo -e "#!/bin/bash\n/usr/local/bin/LoginTracker/.venv/bin/python3 /usr/local/bin/LoginTracker/main_tkinter.py" > ~/Desktop/Login_Tracker
sudo chmod u+x ~/Desktop/Login_Tracker
python3 /usr/local/bin/LoginTracker/main_tkinter.py