import tkinter as tk
from tkinter import ttk, PhotoImage
import gspread
import datetime
import socket
import os
import time
import cv2
from pathlib import Path
from threading import Thread
import logging

start_time = time.time()

# CWD - current working directory, with backslashes replaced by forward slashes
cwd = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")

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


def add_simple_warning(warn_type):
    logging.warning(f"{warn_type}, skipping...")
    ID_label.config(fg="orange")
    ID_label.config(text=warn_type)


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
            [[input_id, timestamp, log_type]],
            f"A{cell_value}:C{cell_value}",
            "USER_ENTERED",
        )
    except:
        add_simple_warning("Error on singleupload")


def batchget(row_number):
    global vital_info
    try:
        vital_info = ID_sheet.batch_get(
            [f"B{row_number+1}:D{row_number+1}", "E2", "E4", "E6"]
        )
    except:
        logging.exception(f"Error during batchget({row_number})")
        add_simple_warning("Error batchget, try again")
        return


# Function to upload data to the spreadsheet
def upload_data(log_type, delete_last_character=False):
    global ID_list
    global ID_list_sum
    global vital_info
    start_time = time.time()
    input_id = entry.get()
    entry.delete(0, tk.END)
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
    upload_timestamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    ID_label.config(text="Working... (Your picture is being taken)")

    batchget(ID_index)

    # Check to see if the lists align
    if int(vital_info[3][0][0]) != ID_list_sum:
        logging.info("Lineup issue, fixing...")
        ID_label.config(text="Realigning List...")
        refresh_ID_list()
        ID_index = ID_list.index(input_id)
        batchget(ID_index)

    cell_value = int(vital_info[1][0][0])
    enough_rows = vital_info[2][0][0]
    person_namestatus = vital_info[0][0]
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
            single_upload("logoutall", cell_value, input_id, upload_timestamp)
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
        single_upload(log_type, cell_value, input_id, upload_timestamp)
        ID_label.config(text=f"{log_type} {person_namestatus[0]}")
    ID_label.config(fg="green")
    logging.info(
        f"{log_type} by {person_namestatus[0]} took {time.time() - start_time} seconds"
    )


# Set style, and add images and static text
logo_file_path = f"{cwd}/logo.png"
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

button_login.pack()
button_logout.pack()
button_logout_all.pack()

# Label for displaying messages
ID_label = tk.Label(window, font=("Helvetica", 32))
ID_label.pack()

# Start the Tkinter main loop
logging.info(
    f"Initialzation completed in {time.time() - start_time} seconds, launching GUI..."
)
window.mainloop()
