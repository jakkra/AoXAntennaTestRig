import argparse, sys, time
from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line
from matplotlib import pyplot as plt

plt.rcParams.update({"text.color": "white"})
import numpy as np
from datetime import datetime
from fpdf import FPDF
import os
import glob
from antenna_controller import AntennaController
from aoa_controller import AoAController
import shutil
import tkinter as tk
from live_plot import LivePlot
from webcam_window import WebcamWindow
from threading import Thread


class AngleCollector:
    def __init__(
        self,
        locate_port1,
        locate_baudrate1,
        locate_ctsrts1,
        locate_port2,
        locate_baudrate2,
        locate_ctsrts2,
        antenna_upside_down
    ):
        self.locate_controller_1 = AoAController(
            locate_port1, locate_baudrate1, locate_ctsrts1, False
        )

        self.locate_controller_2 = AoAController(
            locate_port2, locate_baudrate2, locate_ctsrts2, False
        )

        self.antenna_upside_down = antenna_upside_down

        self.collecting_data = False

        self.collected_data1 = {}
        self.collected_data2 = {}

    def start(self):
        self.locate_controller_1.start()
        self.locate_controller_2.start()

    def stop_collect_angles(self):
        self.collecting_data = False

    def __collect_angles(self, locate_controller, timeout_ms, index, gt_azimuth, gt_elevation):
        startTime = self.current_milli_time()
        raw_result = []
        parsed_result = {}

        while (
            self.current_milli_time() < startTime + timeout_ms
        ) and self.collecting_data:
            data = locate_controller.wait_for_aoa_event()
            if data[1] != None:
                urc = data[0]
                urc_dict = data[1]
                # If we successfully parsed event then save it
                raw_result.append(urc)
                tag_id = urc_dict["instanceId"]
                if tag_id in parsed_result:
                    parsed_result[tag_id].append(urc_dict)
                else:
                    parsed_result[tag_id] = []
                    parsed_result[tag_id].append(urc_dict)
        # Save the result in a map with a tuple of azimuth and tilt as key
        if (index == 0):
            self.collected_data1[(gt_azimuth, gt_elevation)] = (
                raw_result,
                parsed_result,
            )
        else:
            self.collected_data2[(gt_azimuth, gt_elevation)] = (
                raw_result,
                parsed_result,
            )

    def collect_angles(self, timeout_ms, do_plot, gt_azimuth, gt_elevation):
        self.locate_controller_1.flush_input_buffer()
        self.locate_controller_2.flush_input_buffer()
        self.locate_controller_1.enable_aoa()
        self.locate_controller_2.enable_aoa()

        self.collecting_data = True

        thread1 = Thread(target=self.__collect_angles,args=(self.locate_controller_1, timeout_ms, 0, gt_azimuth, gt_elevation))
        thread2 = Thread(target=self.__collect_angles,args=(self.locate_controller_2, timeout_ms, 1, gt_azimuth, gt_elevation))
        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()


    def current_milli_time(self):
        return round(time.time() * 1000)

    def save_collected_data(self):
        now = datetime.now()  # current date and time
        date_time = now.strftime("%d_%m_%Y-%H-%M")
        measurement_name1 = "report_{}_antenna1".format(date_time)
        measurement_name2 = "report_{}_antenna2".format(date_time)

        current_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), measurement_name1)
        os.makedirs(current_dir_path)
        for key, log in self.collected_data1.items():
            with open(os.path.join(current_dir_path, "{}_{}.log".format(key[0], key[1])), "w") as data_file:
                for line in log[0]:
                    data_file.write(line + "\n")

        current_dir_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), measurement_name2)
        os.makedirs(current_dir_path)
        for key, log in self.collected_data2.items():
            with open(os.path.join(current_dir_path, "{}_{}.log".format(key[0], key[1])), "w") as data_file:
                for line in log[0]:
                    data_file.write(line + "\n")

    def clear_collected_data(self):
        self.collected_data1 = {}
        self.collected_data2 = {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AoA Analyzer")

    parser.add_argument(
        "--controller_port",
        dest="controller_port",
        required=True,
        help="Serial port of the antenna controller.",
    )
    parser.add_argument(
        "--controller_baudrate",
        dest="controller_baudrate",
        default=115200,
        required=False,
        help="Baudrate of antenna controller",
    )

    parser.add_argument(
        "--locate_port1",
        dest="locate_port1",
        required=True,
        help="Serial port of u-connectLocate module.",
    )

    parser.add_argument(
        "--locate_port2",
        dest="locate_port2",
        required=True,
        help="Serial port of u-connectLocate module.",
    )

    parser.add_argument(
        "--locate_baudrate",
        dest="locate_baudrate",
        default=115200,
        required=False,
        help="Baudrate for u-connectLocate.",
    )

    parser.add_argument(
        "--no-flow",
        dest="ctsrts",
        action="store_false",
        help="Flag to disable flow control for u-connectLocate, needed to run tests if CTS/RTS are not connected.",
    )

    parser.add_argument(
        "--name",
        dest="name",
        required=False,
        default="",
        help="Name identifying the measurement",
    )

    args = parser.parse_args()

    # Cleanup if there are some old .log files
    for file in glob.glob("*.log"):
        os.remove(os.path.join(os.path.dirname(__file__), file))

    antenna_controller = AntennaController(
        args.controller_port, args.controller_baudrate
    )
    antenna_controller.start()
    antenna_controller.enable_antenna_control()

    angle_collector = AngleCollector(
        args.locate_port1,
        args.locate_baudrate,
        args.ctsrts,
        args.locate_port2,
        args.locate_baudrate,
        args.ctsrts,
        True
    )

    print("Successfully set up communication")
    angle_collector.start()

    # Note must be in even dividable steps
    start_angle = -40
    end_angle = 40
    steps = 20
    millies_per_angle = 7000
    if True:
        antenna_controller.rotate_antenna(start_angle)
        for azimuth_angle in range(start_angle, end_angle + 1, steps):
            antenna_controller.tilt_antenna(start_angle)
            for tilt_angle in range(start_angle, end_angle + 1, steps):
                print(
                    "Sample azimuth: {}, tilt: {}".format(
                        antenna_controller.get_antenna_location()[0],
                        antenna_controller.get_antenna_location()[1],
                    )
                )
                time.sleep(2)  # Give angles some time to stabalize
                angle_collector.collect_angles(
                    millies_per_angle,
                    False,
                    antenna_controller.get_antenna_rotation(),
                    antenna_controller.get_antenna_tilt(),
                )
                antenna_controller.tilt_antenna(steps)
            antenna_controller.tilt_antenna(start_angle - steps)
            antenna_controller.rotate_antenna(steps)

        antenna_controller.rotate_antenna(start_angle - steps)
        antenna_controller.disable_antenna_control()
    else:
        angle_collector.collect_angles(
            millies_per_angle,
            False,
            antenna_controller.get_antenna_rotation(),
            antenna_controller.get_antenna_tilt(),
        )

    angle_collector.save_collected_data()


    print("Finished")
