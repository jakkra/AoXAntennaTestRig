import time
import _thread
import rel
import threading
import sys
import argparse
from antenna_controller import AntennaController

controller = None

menu_options = {
    1: "Enable",
    2: "Azimuth",
    3: "Tilt",
}

def print_menu(options):
    for key in options.keys():
        print(key, "--", options[key])

def handle_enable():
    options = {
        0: "Disable steppers",
        1: "Enable steppers",
    }
    print_menu(options)
    try:
        option = int(input("Enter value: "))
        if option == 0 or option == 1:
            send_set_enable(option)
        else:
            print("Invalid choise", option)
    except:
        print("Wrong input. Please enter a number ...")

def handle_azimuth():
    try:
        value = int(input("Enter value: "))
        send_azimuth(value)
    except:
        print("Wrong input. Please enter a number ...")

def handle_tilt():
    try:
        value = int(input("Enter value: "))
        send_tilt(value)
    except:
        print("Wrong input. Please enter a number ...")

def send_set_enable(enable):
    if enable == 0:
        controller.disable_antenna_control()
    elif enable == 1:
        controller.enable_antenna_control()

def send_azimuth(value):
    controller.rotate_antenna(value)

def send_tilt(value):
    controller.tilt_antenna(value)

def handle_menu():
    time.sleep(2)
    while True:
        print_menu(menu_options)
        option = ""
        try:
            option = int(input("Enter your choice: "))
        except:
            print("Wrong input. Please enter a number ...")
        if option == 1:
            handle_enable()
        elif option == 2:
            handle_azimuth()
        elif option == 3:
            handle_tilt()
        else:
            print("Invalid option. Please enter a number between 1 and 3.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Antenna Controller over UART")

    parser.add_argument("--port", dest="port", required=True)
    parser.add_argument(
        "--baudrate",
        dest="baudrate",
        default=115200,
        required=False,
    )

    args = parser.parse_args()
    controller = AntennaController(args.port, args.baudrate)
    controller.start()
    controller.enable_antenna_control()

    thread = threading.Thread(target=handle_menu)
    thread.daemon = True
    thread.start()

    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()

