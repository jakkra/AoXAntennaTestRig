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
        locate_ports,
        locate_baudrate,
        locate_ctsrts,
        antenna_upside_down,
    ):
        self.locate_controllers = []
        self.collected_data = []
        for port in locate_ports:
            self.locate_controllers.append(
                AoAController(port, locate_baudrate, locate_ctsrts, False)
            )
            self.collected_data.append({})

        self.antenna_upside_down = antenna_upside_down

        self.collecting_data = False

    def start(self):
        for locate in self.locate_controllers:
            locate.start()

    def stop_collect_angles(self):
        self.collecting_data = False

    def __collect_angles(
        self, locate_controller, timeout_ms, index, gt_azimuth, gt_elevation
    ):
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
        self.collected_data[index][(gt_azimuth, gt_elevation)] = (
            raw_result,
            parsed_result,
        )

    def collect_angles(self, timeout_ms, do_plot, gt_azimuth, gt_elevation):
        self.collecting_data = True
        threads = []
        for idx, locate in enumerate(self.locate_controllers):
            locate.flush_input_buffer()
            locate.enable_aoa()
            thread = Thread(
                target=self.__collect_angles,
                args=(locate, timeout_ms, idx, gt_azimuth, gt_elevation),
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)

        for thread in threads:
            try:
                while thread.is_alive():
                    thread.join(1)  # time out not to block KeyboardInterrupt
            except KeyboardInterrupt:
                print("Ctrl+C exit")
                sys.exit(1)

    def current_milli_time(self):
        return round(time.time() * 1000)

    def save_collected_data(self, identifiers=[]):
        now = datetime.now()  # current date and time
        date_time = now.strftime("%d_%m_%Y-%H-%M")

        for i, samples in enumerate(self.collected_data):
            if (len(identifiers) == len(self.collected_data)):
                measurement_name = "report_{}_antenna_{}".format(date_time, identifiers[i])
            else:
                measurement_name = "report_{}_antenna_{}".format(date_time, i)

            current_dir_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)), measurement_name
            )
            os.makedirs(current_dir_path)
            for key, log in samples.items():
                with open(
                    os.path.join(current_dir_path, "{}_{}.log".format(key[0], key[1])),
                    "w",
                ) as data_file:
                    for line in log[0]:
                        data_file.write(line + "\n")


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
        "--locate_ports",
        dest="locate_ports",
        nargs="+",
        required=True,
        help="List of serial ports of u-connectLocate modules.",
    )

    parser.add_argument(
        "--locate_baudrate",
        dest="locate_baudrate",
        default=115200,
        required=False,
        help="Baudrate for u-connectLocate. Note all needs to have same baudrate.",
    )

    parser.add_argument(
        "--no-flow",
        dest="ctsrts",
        action="store_false",
        help="Flag to disable flow control for u-connectLocate, needed to run tests if CTS/RTS are not connected.",
    )

    parser.add_argument(
        "--names",
        dest="names",
        required=False,
        nargs="+",
        default=[],
        help="List of name identifying the measurements. Should be same length as --locate_ports",
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
        args.locate_ports,
        args.locate_baudrate,
        args.ctsrts,
        True,
    )

    print("Successfully set up communication")
    angle_collector.start()

    # Note must be in even dividable steps
    start_angle = -40
    end_angle = 40
    steps = 20
    millies_per_angle = 7000
    if False:
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
            5000,
            False,
            antenna_controller.get_antenna_rotation(),
            antenna_controller.get_antenna_tilt(),
        )

    angle_collector.save_collected_data(args.names)

    print("Finished")
