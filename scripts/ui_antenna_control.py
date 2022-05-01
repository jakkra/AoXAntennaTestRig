import tkinter as tk
import time
import argparse
from antenna_controller import AntennaController

ROTATE_OPTIONS = [1, 2, 5, 10, 20, 45, 90]


class UIController:
    def __init__(self):
        self.is_enabled = False
        self.window = tk.Tk()
        self.window.title("Antenna controller")
        self.window.config(bg="#597678")
        self.create_ui()

    def simulate_button_press(self, button):
        button.config(relief="sunken")

    def simulate_button_idle(self, button):
        button.config(relief="raised")

    def left(self, event=None):
        if event != None:
            self.simulate_button_press(self.left_btn)
            self.window.after(100, self.simulate_button_idle, self.left_btn)
            self.left_btn.invoke()
        else:
            controller.rotate_antenna(-int(self.rotation_amount.get()))
        pass

    def right(self, event=None):
        if event != None:
            self.simulate_button_press(self.right_btn)
            self.window.after(100, self.simulate_button_idle, self.right_btn)
            self.right_btn.invoke()
        else:
            controller.rotate_antenna(int(self.rotation_amount.get()))
        pass

    def up(self, event=None):
        if event != None:
            self.simulate_button_press(self.up_btn)
            self.window.after(100, self.simulate_button_idle, self.up_btn)
            self.up_btn.invoke()
        else:
            controller.tilt_antenna(-int(self.rotation_amount.get()))
        pass

    def down(self, event=None):
        if event != None:
            self.simulate_button_press(self.down_btn)
            self.window.after(100, self.simulate_button_idle, self.down_btn)
            self.down_btn.invoke()
        else:
            controller.tilt_antenna(int(self.rotation_amount.get()))
        pass

    def enable(self, event=None):
        if event != None:
            self.simulate_button_press(self.enable_button)
            self.window.after(100, self.simulate_button_idle, self.enable_button)
            self.enable_button.invoke()
        else:
            if self.is_enabled:
                self.enable_button["bg"] = "red"
            else:
                self.enable_button["bg"] = "green"

            self.is_enabled = not self.is_enabled
            if self.is_enabled:
                controller.enable_antenna_control()
            else:
                controller.disable_antenna_control()

    def create_ui(self):
        self.window.geometry("350x275")
        paddings = {"padx": 5, "pady": 5}

        self.left_btn = tk.Button(self.window, text="←", command=self.left)
        self.left_btn.grid(row=2, column=1, padx=2, pady=2)

        self.right_btn = tk.Button(self.window, text="→", command=self.right)
        self.right_btn.grid(row=2, column=3, padx=2, pady=2)

        self.up_btn = tk.Button(self.window, text="↑", command=self.up)
        self.up_btn.grid(row=1, column=2, padx=2, pady=2)

        self.down_btn = tk.Button(self.window, text="↓", command=self.down)
        self.down_btn.grid(row=3, column=2, padx=2, pady=2)

        self.enable_button = tk.Button(
            self.window, text="O", height=1, width=2, command=self.enable
        )
        self.enable_button.grid(row=2, column=2)
        self.enable_button.config(bg="red", fg="white")

        self.rotation_amount = tk.StringVar(self.window)
        self.rotation_amount.set(ROTATE_OPTIONS[0])  # default value

        self.degree_label = tk.Label(self.window, text="Choose steps in degree")
        self.degree_label.grid(row=4, column=5)
        self.degree_label.config(bg="#597678", fg="white")

        self.degree_dropdown = tk.OptionMenu(
            self.window, self.rotation_amount, *ROTATE_OPTIONS
        )
        self.degree_dropdown.config(bg="dark gray", width=5)
        self.degree_dropdown.grid(row=5, column=5, **paddings)

        col_count, row_count = self.window.grid_size()

        for col in range(col_count):
            self.window.grid_columnconfigure(col, minsize=20)

        for row in range(row_count):
            self.window.grid_rowconfigure(row, minsize=20)

        self.window.bind("<Left>", self.left)
        self.window.bind("<Right>", self.right)
        self.window.bind("<Up>", self.up)
        self.window.bind("<Down>", self.down)
        self.window.bind("<space>", self.enable)
        self.window.mainloop()


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
    ui = UIController()
