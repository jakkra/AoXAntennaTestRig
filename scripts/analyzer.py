import argparse, sys, time
from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line
from matplotlib import pyplot as plt
import numpy as np
from datetime import datetime
from fpdf import FPDF
import os
from antenna_controller import AntennaController
from aoa_controller import AoAController


from live_plot import LivePlot


class AoATester:
    def __init__(
        self,
        locate_port,
        locate_baudrate,
        locate_ctsrts,
        antenna_upside_down=False,
        mock=False,
    ):
        self.locate_controller = AoAController(
            locate_port, locate_baudrate, locate_ctsrts, mock
        )

        self.antenna_upside_down = antenna_upside_down

        # We assume antenna tester is homed and at 0,0
        self.azimuth_angle = 0
        self.tilt_angle = 0
        self.collecting_data = False

        self.figsize = (12, 10)

        self.collected_data = {}
        self.created_images = []

    def start(self):
        self.locate_controller.start()

    def stop_collect_angles(self):
        self.collecting_data = False

    def collect_angles(self, timeout_ms, do_plot, gt_azimuth, gt_elevation):
        self.locate_controller.enable_aoa()
        graph = None
        if do_plot:
            graph = LivePlot(self.figsize, gt_azimuth, gt_elevation)

        startTime = self.current_milli_time()
        raw_result = []
        parsed_result = {}
        self.collecting_data = True

        while (
            self.current_milli_time() < startTime + timeout_ms
        ) and self.collecting_data:
            urc = self.locate_controller.wait_for_uudf()
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

                graph.add_tag_sample(
                    tag_id,
                    urc_dict["azimuth"]
                    if not self.antenna_upside_down
                    else -urc_dict["azimuth"],
                    urc_dict["elevation"]
                    if not self.antenna_upside_down
                    else -urc_dict["elevation"],
                    gt_azimuth,
                    gt_elevation,
                )
        img = graph.save_snapshot_png("{}_{}".format(gt_azimuth, gt_elevation))
        self.created_images.append(img)
        graph.destroy()
        # Save the result in a map with a tuple of azimuth and tilt as key
        self.collected_data[(gt_azimuth, gt_elevation)] = (
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
        }
        return urc_dict

    def current_milli_time(self):
        return round(time.time() * 1000)

    def save_collected_data(self):
        for key, log in self.collected_data.items():
            with open("{}_{}.log".format(key[0], key[1]), "w") as data_file:
                for line in log[0]:
                    data_file.write(line + "\n")

    def clear_collected_data(self):
        self.collected_data = {}
        self.created_images = []

    def create_cdf(self, show_cdfs=True):
        def create_and_style_cdf(data, title):
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
            plt.title(title)
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

        tags_errors = {}
        all_errors_phi = []
        all_errors_theta = []
        # gt_key is a tuple (azimuth_gt, elevation_gt)
        for gt_key, logs_from_location in self.collected_data.items():
            # For each sample in location
            for tag_id, urcs in logs_from_location[1].items():
                azimuth_error = list(
                    map(
                        lambda urc: abs(
                            urc["azimuth"]
                            - (
                                gt_key[0]
                                if not self.antenna_upside_down
                                else -gt_key[0]
                            )
                        ),
                        urcs,
                    )
                )
                theta_error = list(
                    map(
                        lambda urc: abs(
                            urc["elevation"]
                            - (
                                gt_key[1]
                                if not self.antenna_upside_down
                                else -gt_key[1]
                            )
                        ),
                        urcs,
                    )
                )
                all_errors_phi = all_errors_phi + azimuth_error
                all_errors_theta = all_errors_theta + theta_error
                tags_errors[tag_id] = {
                    "azimuth_errors": azimuth_error,
                    "elevation_errors": theta_error,
                }
            plot_num = 1
            fig = plt.figure(figsize=self.figsize)
            fig.patch.set_facecolor("#202124")
            fig.subplots_adjust(wspace=0.15)
            plt.subplots_adjust(
                left=0.05, right=0.95, top=0.94, bottom=0.05, hspace=0.7
            )
            plt.gcf().text(
                0.40,
                0.99,
                "Ground truth ({}, {})".format(gt_key[0], gt_key[1]),
                va="top",
                fontsize=22,
            )

            for tag_id, errors in tags_errors.items():
                plt.subplot(6, 2, plot_num)
                create_and_style_cdf(
                    errors["azimuth_errors"], "Azimuth {}".format(tag_id)
                )
                plot_num = plot_num + 1

                plt.subplot(6, 2, plot_num)
                create_and_style_cdf(
                    errors["elevation_errors"], "Elevation {}".format(tag_id)
                )
                plot_num = plot_num + 1

            img_name = "{}_{}_cdf.png".format(gt_key[0], gt_key[1])
            self.created_images.append(img_name)
            plt.savefig(img_name)
            if show_cdfs:
                plt.show()
            else:
                plt.clf()
                plt.close()

        fig = plt.figure(figsize=self.figsize)
        fig.patch.set_facecolor("#202124")
        fig.subplots_adjust(wspace=0.3)
        plt.subplots_adjust(left=0.05, right=0.95, top=0.94, bottom=0.05, hspace=0.4)
        plt.gcf().text(
            0.40,
            0.99,
            "All tags and positions combined CDF",
            va="top",
            fontsize=22,
        )
        plt.subplot(2, 1, 1)
        create_and_style_cdf(all_errors_phi, "For all tags azimuth")
        plt.subplot(2, 1, 2)
        create_and_style_cdf(all_errors_theta, "For all tags theta")
        plt.savefig("cdf_all_tags.png")
        self.created_images.append("cdf_all_tags.png")
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

    antenna_controller = AntennaController(
        args.controller_port, args.controller_baudrate
    )
    antenna_controller.start()
    antenna_controller.enable_antenna_control()

    tester = AoATester(
        args.locate_port,
        args.locate_baudrate,
        args.ctsrts,
    )

    print("Successfuly set up communication")
    tester.start()
    # Note must be in even dividable steps
    start_angle = -40
    end_angle = 40
    steps = 20

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
            tester.collect_angles(
                10000,
                True,
                antenna_controller.get_antenna_rotation(),
                antenna_controller.get_antenna_tilt(),
            )
            antenna_controller.tilt_antenna(steps)
        antenna_controller.tilt_antenna(start_angle - steps)
        antenna_controller.rotate_antenna(steps)

    antenna_controller.rotate_antenna(start_angle - steps)

    antenna_controller.disable_antenna_control()
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
