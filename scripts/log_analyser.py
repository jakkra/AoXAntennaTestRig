import argparse, sys, time
from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line
from matplotlib import pyplot as plt
import numpy as np
from datetime import datetime
import os
import glob
from pathlib import Path
from antenna_controller import AntennaController
from aoa_controller import AoAController
from analyzer import AoATester

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AoA Analyzer ")

    parser.add_argument(
        "--log_dir",
        dest="log_dir",
        default="./",
        required=False,
        help="Path to folder with log files in.",
    )

    parser.add_argument(
        "--remove_90",
        dest="remove_90",
        default=False,
        required=False,
        help="Drop any angles that are +-90, used for testing.",
    )

    parser.add_argument(
        "--max_angle",
        dest="max_angle",
        default=90,
        required=False,
        help="Drop all angles utside of the range [-max_angle, max_angle].",
    )

    args = parser.parse_args()
    print("Max angle:", args.max_angle)
    print("Log dir:", args.log_dir)

    analyzer = AoATester(None, None, None, False, False, True)
    logs = glob.glob(args.log_dir + "/*.log")
    if len(logs) == 0:
        print("No log files found in {}".format(args.log_dir))

    for logfile in logs:
        filename = Path(logfile).name
        ant_rotation = int(filename.split("_")[0])
        antenna_tilt = int(filename.split("_")[1].split(".log")[0])
        if abs(ant_rotation) <= int(args.max_angle) or abs(antenna_tilt) <= int(
            args.max_angle
        ):
            with open(logfile) as fp:
                data = fp.readlines()
                analyzer.analyze_logs(
                    data, False, ant_rotation, antenna_tilt, args.remove_90
                )
        else:
            print("Skipping:", logfile)
    analyzer.create_plots(show_plots=False, summary_only=True)
    analyzer.create_plots(show_plots=False, summary_only=True, distribution_plot=True)

    analyzer.create_pdf_report(os.path.join(args.log_dir, "log_analyzis_report"))
    analyzer.delete_created_images()

    print("Finished")
