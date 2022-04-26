import websocket
import _thread
import time
import rel
import threading
import sys


def on_message(ws, message):
    print(message)


def on_error(ws, error):
    print(error)


def on_close(ws, close_status_code, close_msg):
    print("### closed ###")


def on_open(ws):
    print("Opened connection")


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
    ws.send("ENABLE={0}".format(enable))


def send_azimuth(value):
    ws.send("AZIMUTH={0}".format(value))


def send_tilt(value):
    ws.send("TILT={0}".format(value))


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
    # websocket.enableTrace(True)

    thread = threading.Thread(target=handle_menu)
    thread.daemon = True
    thread.start()

    ws = websocket.WebSocketApp(
        "ws://192.168.1.19:8080/ws",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    ws.run_forever(dispatcher=rel)  # Set dispatcher to automatic reconnection
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()
    print("Started")
