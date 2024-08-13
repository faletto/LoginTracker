import gspread
import datetime
import socket
import os
import sys
import time
import flask
from pathlib import Path
from threading import Thread

usb_drive_name = "LoginLogger"  # TODO - add config file for this

# CWD - current working directory, with backslashes replaced by forward slashes
cwd = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")
usb_drive_path = f"/media/{os.getlogin()}/{usb_drive_name}"

# If no USB drive (matching usb_drive_name) is plugged in
if not Path(usb_drive_path).is_dir():
    print(f"WARNING - No USB Drive Found at {usb_drive_path}")
    # Creates a virtual "drive" at /home/(username)/Desktop/VirtualDrive
    usb_drive_path = (
        os.path.expanduser("~").replace("\\", "/") + "/Desktop/VirtualDrive"
    )
    # Ensures virtual drive folder exists
    if not os.path.exists(usb_drive_path):
        os.mkdir(usb_drive_path)
    print(f"Using {usb_drive_path} instead")


def write_to_log(text):
    os.system(
        f"""echo "{datetime.datetime.now()}  {text}" >> "{usb_drive_path}"/logs.txt"""
    )


# A warning will simply end the function, while keeping the web server online
def add_simple_warning(warn_type):
    write_to_log(f"WARNING - {warn_type}, skipping...")
    return flask.render_template("index.html", message=warn_type, show_last_login=False)


# An error will shut down the web server
def add_simple_error(error_type, instructions):
    write_to_log(f"ERROR - {error_type}")

    return flask.render_template(
        "error.html", error=error_type, instructions=instructions
    )


# Gives webpage time to load before exiting
def quit():
    time.sleep(0.5)
    sys.exit()

try:
    socket.create_connection(("www.google.com", 80), timeout=3)
except:
    add_simple_error("No internet", "No internet. Please connect to internet")

# Authenticate with Google Sheets
# https://docs.gspread.org/en/latest/oauth2.html#for-end-users-using-oauth-client-id
gc = gspread.oauth(credentials_filename=f"{cwd}/credentials.json")

url_file_path = f"{cwd}/spreadsheet_url.txt"
try:
    with open(url_file_path) as f:
        spreadsheet_url = f.readline()
    write_to_log(f"Opening spreadsheet: {spreadsheet_url}")
    spreadsheet = gc.open_by_url(spreadsheet_url)
except FileNotFoundError:
    with open(url_file_path, "w") as f:
        f.write("")
    add_simple_error(
        "No URL File, Creating...",
        "Please paste spreadsheet URL into the new spreadsheet_url.txt",
    )
except gspread.exceptions.NoValidUrlKeyFound:
    add_simple_error(
        "Invalid or Empty URL File",
        "Please paste spreadsheet URL into spreadsheet_url.txt",
    )
except:
    add_simple_error("Unknown Error", "Unknown Error. Please")

worksheet = spreadsheet.worksheet("[BACKEND] Logs")
ID_sheet = spreadsheet.worksheet("[BACKEND] ID List")

ID_list = ID_sheet.col_values(1)

app = flask.Flask(__name__)

@app.route("/")
def index():
    return flask.render_template("index.html",message="Server Restarted.",show_last_login=False)

def single_upload(log_type, cell_value, input_id):
    worksheet.update(
        [[input_id, datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), log_type]],
        f"A{cell_value}:C{cell_value}",
        "USER_ENTERED",
    )


# Function to upload data to the spreadsheet
@app.route("/upload", methods=["POST"])
def upload():
    global ID_list
    success_message = ""
    # Gets time of upload
    start_time = time.time()

    # Gets current value of student ID
    input_id = flask.request.form["input_id"]

    # Ends script if ID value is empty
    if not input_id:
        return add_simple_warning("Student ID field is empty")
    if not input_id.isnumeric or not 100000 <= int(input_id) <= 9999999:
        return add_simple_warning("Invalid ID")

    # Gets log type
    log_type = flask.request.form["button"]

    try:
        ID_index = ID_list.index(input_id)
    except ValueError:
        ID_list = ID_sheet.col_values(1)
        try:
            ID_index = ID_list.index(input_id)
        except ValueError:
            add_simple_warning("ID Not Found!")
            return
        write_to_log("Found ID in Search")

    vital_info = ID_sheet.batch_get([f"B{ID_index+1}:D{ID_index+1}", "G1", "I1"])
    cell_value = int(vital_info[1][0][0])
    enough_rows = vital_info[2][0][0]
    person_namestatus = vital_info[0][0]
    if person_namestatus[1] == log_type:
        return add_simple_warning("Already Done")
    elif enough_rows == "FALSE":
        worksheet.append_rows(
            [
                [
                    None,
                    None,
                    f'=IF(C{cell_value+i}="logout",B{cell_value+i}-INDEX(FILTER(B$1:B{cell_value+i-1}, C$1:C{cell_value+i-1}="login", A$1:A{cell_value+i-1}=A{cell_value+i}), COUNT(FILTER(B$1:B{cell_value+i-1}, C$1:C{cell_value+i-1}="login", A$1:A{cell_value+i-1}=A{cell_value+i}))),)',
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
                f"B{cell_value}:C{cell_value + len(logged_in_IDs_flat) - 1}",
                "USER_ENTERED",
            )
            success_message = f"Goodnight, {person_namestatus[0]}!"
            write_to_log(f"Logged out {len(logged_in_IDs_flat)} users")
    elif log_type == "logoutall":
        return add_simple_warning(f"{person_namestatus[0]} can't log everyone out.")
    else:
        single_upload(log_type, cell_value, input_id)
        success_message = f"{log_type} {person_namestatus[0]}"
    camera_path = (
        f"'{usb_drive_path}/{person_namestatus[0]}-{datetime.datetime.now().strftime('%Y-%m-%d %H%M%S')}-{log_type}"
        + ".jpeg'"
    )
    os.system(
        f"""fswebcam -r 320x240 --no-banner {camera_path}"""
    )  # https://raspberrypi-guide.github.io/electronics/using-usb-webcams#setting-up-and-using-a-usb-webcam

    # Copies most recent picture to a location where flask can read it
    os.system(f"""cp {camera_path} static/last_login.jpeg""")
    write_to_log(
        f"{log_type} by {person_namestatus[0]} took {time.time() - start_time} seconds"
    )

    return flask.render_template(
        "index.html", message=success_message, show_last_login=True
    )


app.run(debug=True)
