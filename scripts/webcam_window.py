import tkinter as tk
import PIL
from PIL import Image, ImageTk
import cv2
import matplotlib.pyplot as plt


class WebcamWindow:
    def __init__(self, window=None):
        self.window = window
        self.create_webcam()

    def create_webcam(self):
        width, height = 800, 600
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self.window.title("Webcam feed")
        self.lmain = tk.Label(self.window)
        self.lmain.pack()
        self.show_frame()

    def show_frame(self):
        _, frame = self.cap.read()
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        img = PIL.Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.lmain.imgtk = imgtk
        self.lmain.configure(image=imgtk)
        self.lmain.after(10, self.show_frame)
