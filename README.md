# LoginTracker
A work-in-progress Python/Google Sheets sign-in/sign-out system

Keep in mind: this is VERY work-in-progress. Expect stuff to be broken.
Designed exclusively for Debian/Ubuntu, specifically on a Raspberry Pi using a USB webcam. Windows may or may not work.

For a quick (but relatively controversial) way of installing or updating everything:
* Flask: `curl -sSL https://github.com/cj-plusplus/LoginTracker/install.sh | bash`
* Tkinter: `curl -sSL https://github.com/cj-plusplus/LoginTracker/install_tkinter.sh | bash`

I recommend doing the following before installing:
* Create a new gmail account dedicated solely to attendance tracking (for security and in case there's a bug)
* Uninstall Lynx browser, if applicable

On first startup, the app will open a web browser (Chrome recommended) and ask you to give Oauth permissions. As stated before, I recommend using a new account for this. Allow it to access as needed.

To use a different account, delete the authorized_user.json file in ```~/.config/gspread/credentials.json``` (```%APPDATA%\gspread\credentials.json``` for Windows)

Small portions of the Python were done by ChatGPT. I (@TaigaM123) am not sure how much time or effort it saved though.
