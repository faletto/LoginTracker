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

usb_drive_name = "LoginLogger"  # TODO - add config file for this

start_time = time.time()

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


def add_simple_warning(warn_type):
    write_to_log(f"WARNING - {warn_type}, skipping...")
    ID_label.config(fg="orange")
    ID_label.config(text=warn_type)


def add_simple_error(error_type, instructions):
    write_to_log(f"ERROR - {error_type}")
    ID_label = ttk.Label(
        window, text=f"{instructions}, close this window, and try again."
    )
    ID_label.pack()
    window.mainloop()
    quit()


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
except PermissionError:
    add_simple_error(
        "Email not allowed to access spreadsheet",
        "This email doesn't have permission for this spreadsheet. Please fix this,",
    )
except:
    add_simple_error("Unknown Error", "Unknown Error. Please")

worksheet = spreadsheet.worksheet("[BACKEND] Logs")
ID_sheet = spreadsheet.worksheet("[BACKEND] ID List")

ID_list = ID_sheet.col_values(1)


def single_upload(log_type, cell_value, input_id, timestamp):
    try:
        worksheet.update(
            [[input_id, timestamp, log_type]],
            f"A{cell_value}:C{cell_value}",
            "USER_ENTERED",
        )
    except:
        add_simple_warning("Error on singleupload")


# Function to upload data to the spreadsheet
def upload_data(log_type, delete_last_character=False):
    global ID_list
    start_time = time.time()
    input_id = entry.get()
    entry.delete(0, tk.END)
    if delete_last_character:
        input_id = input_id[:-1]
    upload_timestamp = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    if not input_id.isnumeric() or not 100000 <= int(input_id) <= 99999999:
        if input_id:
            add_simple_warning("Invalid ID")
        return
    ID_label.config(fg="black")
    ID_label.config(text="Working...")
    try:
        ID_index = ID_list.index(input_id)
    except:
        ID_list = ID_sheet.col_values(1)
        try:
            ID_index = ID_list.index(input_id)
        except:
            add_simple_warning("ID Not Found!")
            return
        write_to_log("Found ID in Search")

    try:
        vital_info = ID_sheet.batch_get([f"B{ID_index+1}:D{ID_index+1}", "G1", "I1"])
    except ConnectionError:
        add_simple_warning("Not Connected to Internet")
        return
    except:
        add_simple_warning("Error batchget")
        return
    cell_value = int(vital_info[1][0][0])
    enough_rows = vital_info[2][0][0]
    person_namestatus = vital_info[0][0]
    if person_namestatus[1] == log_type:
        add_simple_warning("Already Done")
        return
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

    # Thread(
    #    target=os.system,
    #    args=(
    #        f"""fswebcam -r 320x240 --no-banner '{usb_drive_path}'/'{person_namestatus[0]}-{datetime.datetime.now().strftime("%Y-%m-%d %H%M%S")}-{log_type}'.jpeg""",
    #    ),
    # ).start()  # https://raspberrypi-guide.github.io/electronics/using-usb-webcams
    Thread(
        target=cv2.imwrite,
        args=(
            f"""{usb_drive_path}/{person_namestatus[0]}-{datetime.datetime.now().strftime("%Y-%m-%d %H%M%S")}-{log_type}.jpeg""",
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
            write_to_log(f"Logged out {len(logged_in_IDs_flat)} users")
    elif log_type == "logoutall":
        add_simple_warning(f"{person_namestatus[0]} can't log everyone out.")
        return
    else:
        single_upload(log_type, cell_value, input_id, upload_timestamp)
        ID_label.config(text=f"{log_type} {person_namestatus[0]}")
    ID_label.config(fg="green")
    write_to_log(
        f"{log_type} by {person_namestatus[0]} took {time.time() - start_time} seconds"
    )


# Set style, and add images and static text
logo_file_path = f"{cwd}/logo.png"
try:
    image = PhotoImage(file=logo_file_path)
    image_label = ttk.Label(window, image=image)
    image_label.pack()
except:
    write_to_log("WARNING - No Logo Image Found")

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
write_to_log(
    f"Initialzation completed in {time.time() - start_time} seconds, launching GUI..."
)
window.mainloop()
