import gspread
import datetime
import socket
import os
import sys
import time
import flask
from pathlib import Path
from threading import Thread

# CWD - current working directory
cwd = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")

# TODO - add config file for this
usb_drive_name = "LoginLogger"
usb_drive_path = f"/media/{os.getlogin()}/{usb_drive_name}"

# If no USB drive (matching usb_drive_name) is plugged in
if not Path(usb_drive_path).is_dir():
    print(f"WARNING - No USB Drive Found at {usb_drive_path}")
    # Creates a virtual "drive" at /home/(username)/Desktop/VirtualDrive
    usb_drive_path = os.path.expanduser("~").replace("\\","/") +  "/Desktop/VirtualDrive"
    # Ensures virtual drive folder exists
    if not os.path.exists(usb_drive_path):
        os.mkdir(usb_drive_path)
    print(f"Using {usb_drive_path} instead")

### Various functions that taiga wrote

def write_to_log(text):
    if Path(usb_drive_path).is_dir():
        os.system(
            f"""echo "{datetime.datetime.now()}  {text}" >> "{usb_drive_path}"/logs.txt"""
        )
    else:
        print(f"{datetime.datetime.now()}  {text}")


# A warning will simply end the function, while keeping the web server online
def add_simple_warning(warn_type):
    write_to_log(f"WARNING - {warn_type}, skipping...")
    return flask.render_template("index.html", message=warn_type,show_last_login=False)

# An error will shut down the web server
def add_simple_error(error_type, instructions):
    write_to_log(f"ERROR - {error_type}")
    
    return flask.render_template("error.html",error=error_type,instructions=instructions)

# Gives webpage time to load before exiting
def quit():
    time.sleep(0.5)
    sys.exit()


# Cleans up last login picture from previous session
if os.path.exists(f"{cwd}/static/last_login.jpeg"):
    os.remove(f"{cwd}/static/last_login.jpeg")


# check if there's a not-empty spreadsheet_url.txt file. Does not check for validity.
url_file_path = f"{cwd}/spreadsheet_url.txt"
try:
    if os.path.getsize(url_file_path) == 0:
        add_simple_error(
            "Empty URL File", "Please paste spreadsheet URL into spreadsheet_url.txt"
        )
    with open(url_file_path) as f:
        spreadsheet_url = f.readline()
except:
    with open(url_file_path, "w") as f:
        f.write("")
    add_simple_error(
        "No URL File, Creating...",
        "Please paste spreadsheet URL into the new spreadsheet_url.txt",
    )

# Check internet connection
try:
    socket.setdefaulttimeout(3)
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
except socket.error:
    add_simple_error("No internet", "No Internet. Please reconnect")

# Check for service account credentials
# https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account
service_account_file_path = f"{cwd}/service_account.json"
if not Path(service_account_file_path).is_file():
    add_simple_error("No service_account.json", "Please add a service_account.json")


app = flask.Flask(__name__)

@app.route("/")
def index():
    return flask.render_template("index.html",message="Server Restarted.",show_last_login=False)

# Authenticate with Google Sheets
gc = gspread.service_account(filename=service_account_file_path)

write_to_log(f"Opening spreadsheet: {spreadsheet_url}")
spreadsheet = gc.open_by_url(spreadsheet_url)

worksheet = spreadsheet.worksheet("[BACKEND] Logs")
ID_sheet = spreadsheet.worksheet("[BACKEND] ID List")


def single_upload(log_type, cell_value, input_id):
    worksheet.update(
        [[input_id, datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), log_type]],
        f"A{cell_value}:C{cell_value}",
        "USER_ENTERED",
    )


# Function to upload data to the spreadsheet
@app.route("/upload",methods=["POST"])
def upload():
    success_message = ""
    # Gets time of upload
    start_time = time.time()
    
    # Gets current value of student ID
    input_id = flask.request.form["input_id"]

    # Ends script if ID value is empty
    if not input_id:
        return add_simple_warning("Student ID field is empty")
    if not input_id.isnumeric:
        return add_simple_warning("Invalid ID")

    # Gets log type
    log_type = flask.request.form["button"]

    # Finds the cell associated with that student ID
    person_cell = ID_sheet.find(input_id)
    if person_cell is None:
        return add_simple_warning("Invalid ID")

    else:
        
        vital_info = ID_sheet.batch_get(
            [f"B{person_cell.row}:D{person_cell.row}", "G1", "I1"]
        )
        cell_value = int(vital_info[1][0][0])
        enough_rows = vital_info[2][0][0]
        person_namestatus = vital_info[0][0]
        if person_namestatus[1] == log_type and not log_type == "logoutall":
            return add_simple_warning("Already Done")
        else:
            if enough_rows == "FALSE":
                worksheet.append_rows(
                    [
                        [
                            None,
                            None,
                            f"""=IFERROR(VLOOKUP(A{cell_value+i},'[BACKEND] ID List'!A:B,2,FALSE))""",
                        ]
                        for i in range(200)
                    ],
                    "USER_ENTERED",
                )
                write_to_log("Appended 200 new rows")
            if log_type == "logoutall" and person_namestatus[2] == "TRUE":
                logged_in_cells = ID_sheet.findall("login", None, 3)
                if logged_in_cells == []:
                    return add_simple_warning("Everyone's already logged out!")
                else:
                    logged_in_IDs_nested = ID_sheet.batch_get(
                        [f"A{x.row}" for x in logged_in_cells]
                    )
                    logged_in_IDs_flat = [
                        [int(inner_list[0][0])] for inner_list in logged_in_IDs_nested
                    ]
                    single_upload("logoutall", cell_value, input_id)
                    cell_value += 1
                    worksheet.update(
                        logged_in_IDs_flat,
                        f"A{cell_value}:A{cell_value + len(logged_in_IDs_flat) - 1}",
                    )
                    batchlogoutdate = [
                        [
                            datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                            "logout",
                        ]
                    ] * len(logged_in_IDs_flat)
                    worksheet.update(
                        batchlogoutdate,
                        f"B{cell_value}:C{cell_value + len(logged_in_IDs_flat) - 1}","USER_ENTERED"
                    )
                    success_message = f"Goodnight, {person_namestatus[0]}!"
                    write_to_log(f"Logged out {len(logged_in_IDs_flat)} users")
            elif log_type == "logoutall":
                return add_simple_warning(f"{person_namestatus[0]} can't log everyone out.")
            else:
                single_upload(log_type, cell_value, input_id)
                success_message = f"{log_type} {person_namestatus[0]}"
            camera_path = f"\'{usb_drive_path}/{person_namestatus[0]}-{datetime.datetime.now().strftime('%Y-%m-%d %H%M%S')}-{log_type}" + ".jpeg\'"
            os.system(
                f"""fswebcam -r 320x240 --no-banner {camera_path}"""
            )  # https://raspberrypi-guide.github.io/electronics/using-usb-webcams#setting-up-and-using-a-usb-webcam
            
            # Copies most recent picture to a location where flask can read it
            os.system(f"""cp {camera_path} static/last_login.jpeg""")
            write_to_log(
                f"{log_type} by {person_namestatus[0]} took {time.time() - start_time} seconds"
            )
    
    return flask.render_template("index.html",message=success_message,show_last_login=True)

app.run(debug=True)
