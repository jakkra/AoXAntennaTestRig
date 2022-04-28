import argparse, sys, time
from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line
from matplotlib import pyplot as plt
import numpy as np
from datetime import datetime
from fpdf import FPDF
import os

from live_plot import LivePlot


class AoATester:
    def __init__(
        self,
        controller_port,
        controller_baudrate,
        locate_port,
        locate_baudrate,
        locate_ctsrts,
        antenna_upside_down=False,
    ):
        self.controller_port = controller_port
        self.controller_baudrate = controller_baudrate
        self.locate_port = locate_port
        self.locate_baudrate = locate_baudrate
        self.locate_ctsrts = locate_ctsrts
        self.antenna_upside_down = antenna_upside_down

        # We assume antenna tester is homed and at 0,0
        self.azimuth_angle = 0
        self.tilt_angle = 0

        self.figsize = (12, 10)

        self.collected_data = {}
        self.created_images = []

    def start(self):
        self.ser_controller = open_port(self.controller_port, self.controller_baudrate)
        self.ser_locate = open_port(
            self.locate_port, self.locate_baudrate, self.locate_ctsrts
        )

        # Turn off everything while also checking that communication is working
        controller_ok = send_command_and_wait_rsp(ser_controller, "ENABLE=0")
        locate_ok = send_command_and_wait_rsp(ser_locate, "AT+UDFENABLE=0")

        if controller_ok == -1:
            raise TimeoutError("Failed communcate with Antenna controller")
        if locate_ok == -1:
            raise TimeoutError("Failed communcate with u-connectLocate")

    def enable_antenna_control(self):
        res = send_command_and_wait_rsp(ser_controller, "ENABLE=1")
        if res == -1:
            raise Exception("Failed enabling antenna!")

    def disable_antenna_control(self):
        res = send_command_and_wait_rsp(ser_controller, "ENABLE=0")
        if res == -1:
            raise Exception("Failed disable antenna!")

    def rotate_antenna(self, degree):
        res = send_command_and_wait_rsp(ser_controller, "AZIMUTH={}".format(degree), 10)
        if res == -1:
            raise Exception("Failed rotating antenna!")
        self.azimuth_angle = self.azimuth_angle + degree

    def tilt_antenna(self, degree):
        res = send_command_and_wait_rsp(ser_controller, "TILT={}".format(degree), 10)
        if res == -1:
            raise Exception("Failed rotating antenna!")
        self.tilt_angle = self.tilt_angle + degree

    # TODO if we want differnt GT for each tag
    def get_gt_azimuth(self, tag_id):
        if self.antenna_upside_down:
            return -self.azimuth_angle
        else:
            return self.azimuth_angle

    def get_gt_elevation(self, tag_id):
        if self.antenna_upside_down:
            return -self.tilt_angle
        else:
            return self.tilt_angle

    def collect_angles(self, timeout_ms, do_plot=False):
        resp = send_command_and_wait_rsp(ser_locate, "AT+UDFENABLE=1", 10)
        assert resp != -1
        graph = None
        if do_plot:
            graph = LivePlot(self.figsize, self.azimuth_angle, self.tilt_angle)

        startTime = self.current_milli_time()
        raw_result = []
        parsed_result = {}
        while self.current_milli_time() < startTime + timeout_ms:
            urc = read_line(ser_locate)
            if len(urc) > 0:
                if "+STARTUP" in urc:
                    raise Exception("Module crash detected")
                urc_dict = self.parse_uudf(urc)
                if urc_dict == None:
                    continue
                # If we successfully parsed event then save it
                raw_result.append(urc)
                tag_id = urc_dict["instanceId"]
                if tag_id in parsed_result:
                    parsed_result[tag_id].append(urc_dict)
                else:
                    parsed_result[tag_id] = []
                    parsed_result[tag_id].append(urc_dict)

                # TODO Actual ground truth is not same for all tags, handle that here, for now assume all at same spot.
                graph.add_tag_sample(
                    tag_id,
                    urc_dict["azimuth"],
                    urc_dict["elevation"],
                    self.get_gt_azimuth(tag_id),
                    self.get_gt_elevation(tag_id),
                )
        img = graph.save_snapshot_png(
            "{}-{}".format(self.azimuth_angle, self.tilt_angle)
        )
        self.created_images.append(img)
        graph.destroy()
        # Save the result in a map with a tuple of azimuth and tilt as key
        self.collected_data[(self.azimuth_angle, self.tilt_angle)] = (
            raw_result,
            parsed_result,
        )
        return (raw_result, parsed_result)

    def parse_uudf(self, urc_str):
        splitted = urc_str.find(":")

        urc, r = urc_str[:splitted], urc_str[splitted:]
        if urc.upper() != "+UUDF":
            return None

        urc_params = r.split(",")
        instanceId = urc_params[0][1:]

        urc_dict = {
            "instanceId": instanceId,
            "rssi": int(urc_params[1]),
            "azimuth": int(urc_params[2]),
            "elevation": int(urc_params[3]),
            "rssi2": int(urc_params[4]),
            "channel": int(urc_params[5]),
            "anchor_id": urc_params[6].replace('"', ""),
            "user_defined_str": urc_params[7].replace('"', ""),
            "timestamp_ms": int(urc_params[8]),
            # Also input the ground truth, might be useful later
            "azimuth_gt": self.get_gt_azimuth(instanceId),
            "elevation_gt": self.get_gt_elevation(instanceId),
        }
        return urc_dict

    def current_milli_time(self):
        return round(time.time() * 1000)

    def save_collected_data(self):
        for key, log in self.collected_data.items():
            with open("{}_{}.log".format(key[0], key[1]), "w") as data_file:
                for line in log[0]:
                    data_file.write(line + "\n")

    def create_cdf(self, show_cdfs=True):
        tags_errors = {}
        # gt_key is a tuple (azimuth_gt, elevation_gt)
        for gt_key, logs_from_location in self.collected_data.items():
            # For each sample in location
            for tag_id, urcs in logs_from_location[1].items():
                tags_errors[tag_id] = {
                    "azimuth_errors": list(
                        map(lambda urc: abs(urc["azimuth"] - urc["azimuth_gt"]), urcs)
                    ),
                    "elevation_errors": list(
                        map(
                            lambda urc: abs(urc["elevation"] - urc["elevation_gt"]),
                            urcs,
                        )
                    ),
                }
            plot_num = 1
            fig = plt.figure(figsize=self.figsize)
            fig.patch.set_facecolor("#202124")
            fig.subplots_adjust(wspace=0.09)
            plt.subplots_adjust(
                left=0.05, right=0.95, top=0.94, bottom=0.05, hspace=0.4
            )
            plt.gcf().text(
                0.40,
                0.99,
                "Ground truth ({}, {})".format(gt_key[0], gt_key[1]),
                va="top",
                fontsize=22,
            )

            def create_and_style_cdf(data, name):
                cdf_color = "green"
                if sum(i <= 10 for i in data) / len(data) < 0.9:
                    cdf_color = "red"

                bins = range(min(data), max(data) + 1, 1)  # Equally distributed
                plt.hist(
                    data,
                    bins=bins,
                    density=True,
                    cumulative=True,
                    label="CDF",
                    histtype="bar",
                    alpha=0.9,
                    color=cdf_color,
                )
                plt.title("{} {}".format(tag_id, name))
                plt.axvline(x=10)
                plt.xlabel("Angle error", {"color": "white"})
                plt.ylabel("Percent", {"color": "white"})
                plt.gca().set_xlim(0)
                plt.gca().set_ylim(0, 1)
                plt.gca().xaxis.label.set_color("white")
                plt.gca().yaxis.label.set_color("white")
                plt.gca().tick_params(axis="x", colors="white")
                plt.gca().tick_params(axis="y", colors="white")
                plt.gca().grid(alpha=0.4, color="#212F3D")

            for tag_id, errors in tags_errors.items():
                plt.subplot(6, 2, plot_num)
                create_and_style_cdf(errors["azimuth_errors"], "Azimuth")
                plot_num = plot_num + 1

                plt.subplot(6, 2, plot_num)
                create_and_style_cdf(errors["elevation_errors"], "Elevation")
                plot_num = plot_num + 1

            img_name = "{}-{}_cdf.png".format(gt_key[0], gt_key[1])
            self.created_images.append(img_name)
            plt.savefig(img_name)
            if show_cdfs:
                plt.show()

    def create_pdf_report(self, name):
        pdf = FPDF()
        for image in self.created_images:
            pdf.add_page()
            # 210 is width of A4 page to keep aspect ratio
            # of figures created with plt.figure(figsize=(12, 10))
            # TODO should probbaly just check aspect ratio of the images instead
            pdf.image(image, 0, 0, 210, int(210 * self.figsize[1] / self.figsize[0]))
        pdf.output("{}.pdf".format(name), "F")

    def delete_created_images(self):
        for img in self.created_images:
            os.remove(img)

    def get_antenna_location(self):
        return (self.azimuth_angle, self.tilt_angle)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AoA Analyzer")

    parser.add_argument("--controller_port", dest="controller_port", required=True)
    parser.add_argument(
        "--controller_baudrate",
        dest="controller_baudrate",
        default=115200,
        required=False,
    )

    parser.add_argument("--locate_port", dest="locate_port", required=True)
    parser.add_argument(
        "--locate_baudrate", dest="locate_baudrate", default=115200, required=False
    )

    parser.add_argument(
        "--no-flow",
        dest="ctsrts",
        action="store_false",
        help="Flag to disable flow control, needed to run tests if CTS/RTS are not connected",
    )

    args = parser.parse_args()

    ser_controller = open_port(args.controller_port, args.controller_baudrate)
    ser_locate = open_port(args.locate_port, args.locate_baudrate, args.ctsrts)

    tester = AoATester(
        args.controller_port,
        args.controller_baudrate,
        args.locate_port,
        args.locate_baudrate,
        args.ctsrts,
    )
    print("Successfuly set up communication")
    tester.start()
    tester.enable_antenna_control()
    # Note must be in even dividable steps
    start_angle = -60
    end_angle = 60
    steps = 10

    tester.rotate_antenna(start_angle)

    for azimuth_angle in range(start_angle, end_angle + 1, steps):
        tester.tilt_antenna(start_angle)
        for tilt_angle in range(start_angle, end_angle + 1, steps):
            print(
                "Sample azimuth: {}, tilt: {}".format(
                    tester.get_antenna_location()[0], tester.get_antenna_location()[1]
                )
            )
            tester.collect_angles(2000, True)
            tester.tilt_antenna(steps)
        tester.tilt_antenna(start_angle - steps)
        tester.rotate_antenna(steps)

    tester.rotate_antenna(start_angle - steps)

    tester.disable_antenna_control()
    tester.save_collected_data()
    tester.create_cdf(False)

    now = datetime.now()  # current date and time
    date_time = now.strftime("%d_%m_%Y-%H-%M")
    pdf_report_name = "report_{}".format(date_time)
    print("Saving PDF: ", pdf_report_name)
    print("Note, it will take some time...")
    tester.create_pdf_report(pdf_report_name)
    tester.delete_created_images()

    print("Finished")
