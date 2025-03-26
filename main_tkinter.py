import tkinter as tk
from tkinter import ttk, PhotoImage
import gspread
import datetime
import socket
import os
import time
import cv2
from threading import Thread
import logging

start_time = time.time()

VERSION = "1.2.0"
HOSTNAME = socket.gethostname()

# CWD - current working directory, with backslashes replaced by forward slashes
cwd = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")

tm_on = os.path.exists(f"{cwd}/time-machine")

if not os.path.exists(f"{cwd}/photos"):
    os.mkdir(f"{cwd}/photos")

# start logger with info
logging.basicConfig(
    filename=f"tracker.log",
    encoding="utf-8",
    filemode="a",
    format="{asctime}:{levelname}:{name}:{message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


# warnings quit the login/out sequence if applicable but otherwise allow continuation
def add_simple_warning(warn_type):
    logging.warning(f"{warn_type}, skipping...")
    ID_label.config(fg="orange")
    ID_label.config(text=warn_type)


# errors kill the program
def add_simple_error(error_type, instructions):
    logging.error(error_type)
    ID_label = ttk.Label(
        window, text=f"{instructions}, close this window, and try again."
    )
    ID_label.pack()
    window.mainloop()
    quit()


def refresh_ID_list():
    global ID_list
    global ID_list_sum
    logging.info("Refreshing ID List...")
    ID_list = ID_sheet.col_values(1)
    ID_list_sum = 0
    for s in ID_list:
        try:
            ID_list_sum += int(s)
        except:
            pass


# Initialize the Tkinter window
window = tk.Tk()
window.title("NRG Login System")

# Authenticate with Google Sheets
# https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account
service_account_file_path = f"{cwd}/service_account.json"
try:
    gc = gspread.service_account(filename=service_account_file_path)
except:
    add_simple_error("No service_account.json", "Please add a service_account.json")

try:
    socket.create_connection(("www.google.com", 80), timeout=3)
except:
    add_simple_error("No internet", "No internet. Please connect to internet")

# open the spreadsheet url and account for a whole bunch of different possible errors
url_file_path = f"{cwd}/spreadsheet_url.txt"
try:
    with open(url_file_path) as f:
        spreadsheet_url = f.readline()
    logging.info(f"Opening spreadsheet: {spreadsheet_url}")
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
except PermissionError:
    add_simple_error(
        "Email not allowed to access spreadsheet",
        "This email doesn't have permission for this spreadsheet. Please fix this,",
    )
except:
    add_simple_error("Unknown Error", "Unknown Error. Please")

worksheet = spreadsheet.worksheet("[BACKEND] Logs")
ID_sheet = spreadsheet.worksheet("[BACKEND] ID List")
refresh_ID_list()


def single_upload(log_type, cell_value, input_id, timestamp):
    try:
        worksheet.update(
            [[input_id, timestamp, log_type, f"{HOSTNAME} {VERSION}"]],
            f"A{cell_value}:D{cell_value}",
            "USER_ENTERED",
        )
    except:
        logging.exception(f"Error during singleupload({cell_value})")
        add_simple_warning("Error on singleupload")
        return True
    return False


def batchget(row_number):
    try:
        vital_info = ID_sheet.batch_get(
            [f"B{row_number+1}:D{row_number+1}", "E2", "E4", "E6"]
        )
    except:
        logging.exception(f"Error during batchget({row_number})")
        add_simple_warning("Error batchget, try again")
        return 1
    return vital_info


# Function to upload data to the spreadsheet
def upload_data(log_type, delete_last_character=False):
    global ID_list
    global ID_list_sum
    start_time = time.time()
    input_id = entry.get()
    entry.delete(0, tk.END)
    logging.info(f"Attempting {log_type}...")
    if delete_last_character:
        input_id = input_id[:-1]
    if not input_id.isnumeric() or not 100000 <= int(input_id) <= 99999999:
        if input_id:
            add_simple_warning("Invalid ID")
        return
    ID_label.config(fg="black")
    try:
        ID_index = ID_list.index(input_id)
    except:
        ID_label.config(text="Looking for your ID...")
        refresh_ID_list()
        try:
            ID_index = ID_list.index(input_id)
        except:
            add_simple_warning("ID Not Found!")
            return
        logging.info("Found ID in Search")

    ID_label.config(text="Taking Pictures...")

    vital_info = batchget(ID_index)
    if vital_info == 1:
        return

    # Check to see if the lists align
    if int(vital_info[3][0][0]) != ID_list_sum:
        logging.info("Lineup issue, fixing...")
        ID_label.config(text="Realigning List...")
        refresh_ID_list()
        ID_index = ID_list.index(input_id)
        vital_info = batchget(ID_index)
        if vital_info == 1:
            return

    cell_value = int(vital_info[1][0][0])
    enough_rows = vital_info[2][0][0]
    person_namestatus = vital_info[0][0]

    # Checks if Time Machine is enabled
    if tm_shown.get():
        # Checks for user permissions
        if person_namestatus[2] == "TRUE":
            # Sets timestamp to what's specified in Time Machine
            upload_timestamp = parse_timestamp(
                year.get(),
                month_list.index(month.get()) + 1,
                day.get(),
                hour.get(),
                minute.get(),
                ap.get(),
            )
            if upload_timestamp == "invalid date :P":
                add_simple_warning("Timestamp is invalid.")
                return
        else:
            add_simple_warning(f"{person_namestatus[0]} cannot modify timestamp.")
            return
    else:
        # Sets timestamp to current time
        upload_timestamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    if person_namestatus[1] == log_type:
        add_simple_warning(f"{person_namestatus[0]} {log_type} already done")
        return
    elif enough_rows == "FALSE":
        worksheet.append_rows(
            [
                [
                    "",
                ]
                for i in range(1000)
            ],
            "USER_ENTERED",
        )
        logging.info("Appended 1000 new rows")

    Thread(
        target=cv2.imwrite,
        args=(
            f"""{cwd}/photos/{person_namestatus[0]}-{datetime.datetime.now().strftime("%Y-%m-%d %H%M%S")}-{log_type}.jpeg""",
            cv2.VideoCapture(0).read()[1],
        ),  # Uses the OpenCV library to make the webcam work on Windows/Mac/Linux
    ).start()
    if log_type == "logoutall" and person_namestatus[2] == "TRUE":
        logged_in_cells = ID_sheet.findall("login", None, 3)
        if logged_in_cells == []:
            add_simple_warning("Everyone's already logged out!")
            return
        else:
            logged_in_IDs_nested = ID_sheet.batch_get(
                [f"A{x.row}" for x in logged_in_cells]
            )
            logged_in_IDs_flat = [
                [int(inner_list[0][0])] for inner_list in logged_in_IDs_nested
            ]
            if single_upload("logoutall", cell_value, input_id, upload_timestamp):
                return
            cell_value += 1
            worksheet.update(
                logged_in_IDs_flat,
                f"A{cell_value}:A{cell_value + len(logged_in_IDs_flat) - 1}",
            )
            batchlogoutdate = [
                [
                    f"=B{cell_value-1}",
                    "logout",
                ]
            ] * len(logged_in_IDs_flat)
            worksheet.update(
                batchlogoutdate,
                f"B{cell_value}:C{cell_value + len(logged_in_IDs_flat) - 1}",
                "USER_ENTERED",
            )
            ID_label.config(text=f"Goodnight, {person_namestatus[0]}!")
            logging.info(f"Logged out {len(logged_in_IDs_flat)} users")
    elif log_type == "logoutall":
        add_simple_warning(f"{person_namestatus[0]} can't log everyone out.")
        return
    else:
        if single_upload(log_type, cell_value, input_id, upload_timestamp):
            return
        ID_label.config(text=f"{log_type} {person_namestatus[0]}")
    ID_label.config(fg="green")
    logging.info(
        f"{log_type} by {person_namestatus[0]} took {time.time() - start_time} seconds"
    )


# Set style, and add images and static text
# Renders smaller logo if Time Machine is enabled to save space
logo_file_path = f"{cwd}/{'logo_400px' if tm_on else 'logo'}.png"

try:
    image = PhotoImage(file=logo_file_path)
    image_label = ttk.Label(window, image=image)
    image_label.pack()
except:
    logging.warning("No Logo Image Found")

window.attributes("-fullscreen", True)
window.focus_force()
window.bind("<Escape>", lambda event: window.attributes("-fullscreen", False))
s = ttk.Style()
s.configure(".", font=("Helvetica", 32))
how_to_use_label = ttk.Label(window, text="Enter your Student ID:")
how_to_use_label.pack()

# Entry widget for user input
entry = ttk.Entry(window, font=("helvetica", 32), justify="center", show="•")
entry.focus_set()
entry.bind("/",lambda event: Thread(target=upload_data, args=("login",True)).start())  # fmt: skip
entry.bind("*",lambda event: Thread(target=upload_data, args=("logout",True)).start())  # fmt: skip
entry.bind("-",lambda event: Thread(target=upload_data, args=("logoutall",True)).start())  # fmt: skip
entry.bind("<Return>",lambda event: Thread(target=upload_data, args=("login",False)).start())  # fmt: skip
entry.pack()

# Buttons for login, logout, and logout all
button_login = ttk.Button(
    window,
    text="Login (/)",
    width=25,
    command=lambda: Thread(target=upload_data, args=("login",)).start(),
)
button_logout = ttk.Button(
    window,
    text="Logout (*)",
    width=25,
    command=lambda: Thread(target=upload_data, args=("logout",)).start(),
)
button_logout_all = ttk.Button(
    window,
    text="Logout All (-)",
    width=25,
    command=lambda: Thread(target=upload_data, args=("logoutall",)).start(),
)

# Temporary feature to test time machine
# button_test_tm = ttk.Button(
#    window,
#    text="Test time machine",
#    width=25,
#    command=lambda: Thread(target=print, args=(str(parse_timestamp(
#                year.get(),
#                month_list.index(month.get()) + 1,
#                day.get(),
#                hour.get(),
#                minute.get(),
#                ap.get()
#            )),)).start()
# )

button_login.pack()
button_logout.pack()
button_logout_all.pack()

tm_shown = tk.BooleanVar()
checkbox_tm_toggle = ttk.Checkbutton(
    window,
    style="TCheckbutton",
    text="Time Machine",
    width=11.75,
    command=lambda: Thread(target=show_tm).start(),
    variable=tm_shown,
)

if tm_on:
    checkbox_tm_toggle.pack()

frame_tm = ttk.Frame(
    window,
    width=600,
    height=200,
)

month_list = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
month = tk.StringVar(value=datetime.datetime.now().strftime("%B"))
tm_month = ttk.Spinbox(frame_tm, values=month_list, wrap=True, textvariable=month)
tm_month.pack(side="left")


day = tk.IntVar(value=datetime.datetime.now().day)
tm_day = ttk.Spinbox(
    frame_tm,
    from_=1,
    to=31,  # calendar.monthrange(year.get(), month_list.index(month.get()) + 1)[1] was trying to get this to update dynamically but no dice
    wrap=True,
    textvariable=day,
)
tm_day.pack(side="left")

year = tk.IntVar(value=datetime.datetime.now().year)
tm_year = ttk.Spinbox(
    frame_tm, from_=2000, to=2100, increment=1, wrap=True, textvariable=year
)
tm_year.pack(side="left")


hour = tk.IntVar(value=int(datetime.datetime.now().strftime("%I")))
tm_hour = ttk.Spinbox(frame_tm, from_=1, to=12, wrap=True, textvariable=hour)
tm_hour.pack(side="left", padx=(15, 0))

minute_values = [("0" + str(i)) for i in range(10)] + [str(i) for i in range(10, 60)]
minute = tk.StringVar(value=datetime.datetime.now().strftime("%M"))
tm_minute = ttk.Spinbox(
    frame_tm, from_=0, to=59, wrap=True, values=minute_values, textvariable=minute
)
tm_minute.pack(side="left")

ap_list = ["AM", "PM"]
ap = tk.StringVar(value=datetime.datetime.now().strftime("%p"))
tm_ap = ttk.Spinbox(frame_tm, values=ap_list, wrap=True, textvariable=ap)
tm_ap.pack(side="left")


def show_tm():
    if tm_shown.get():
        frame_tm.pack()
    else:
        frame_tm.pack_forget()


# Re-formats time format into %m/%d/%Y, %H:%M:%S
# Seconds are hard-coded as 00 (not an option in time machine)
def parse_timestamp(_year, _month, _day, _hour, _minute, _ap):
    # Validate date
    try:
        datetime.datetime(_year, _month, _day)
    except:
        return "invalid date :P"

    # Year doesn't need to be formatted
    # Format month
    month = str(_month) if _month >= 10 else "0" + str(_month)
    # Format day
    day = str(_day) if _day >= 10 else "0" + str(_day)
    # Format hour
    # Check for hour edge cases
    if _hour == 12:
        # Midnight
        if _ap == "AM":
            hour = "00"
        # Noon
        if _ap == "PM":
            hour = "12"
    else:
        if _ap == "PM":
            _hour += 12
        hour = str(_hour) if _hour >= 10 else "0" + str(_hour)

    # Return formatted string
    return f"{month}/{day}/{_year}, {hour}:{_minute}:00"


# Label for displaying messages
ID_label = tk.Label(window, font=("Helvetica", 32))
ID_label.pack()

# Start the Tkinter main loop
logging.info(
    f"Startup of {VERSION} on {HOSTNAME} done in {time.time() - start_time} seconds, launching GUI..."
)
window.mainloop()
