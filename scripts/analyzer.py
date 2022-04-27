import argparse, sys, time
from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line
from matplotlib import pyplot as plt
import numpy as np

from live_plot import LivePlot


class AoATester:
    def __init__(
        self,
        controller_port,
        controller_baudrate,
        locate_port,
        locate_baudrate,
        locate_ctsrts,
    ):
        self.controller_port = controller_port
        self.controller_baudrate = controller_baudrate
        self.locate_port = locate_port
        self.locate_baudrate = locate_baudrate
        self.locate_ctsrts = locate_ctsrts

        # We assume antenna tester is homed and at 0,0
        self.azimuth_angle = 0
        self.tilt_angle = 0

        self.collected_data = {}

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

    def collect_angles(self, timeout_ms, do_plot=False):
        resp = send_command_and_wait_rsp(ser_locate, "AT+UDFENABLE=1", 10)
        assert resp != -1
        graph = None
        if do_plot:
            graph = LivePlot()

        startTime = self.current_milli_time()
        raw_result = []
        parsed_result = {}
        while self.current_milli_time() < startTime + timeout_ms:
            urc = read_line(ser_locate)
            print(urc)
            if len(urc) > 0:
                if "+STARTUP" in urc:
                    raise Exception("Module crash detected")
                urc_dict = self.parse_uudf(urc)
                if urc_dict == None:
                    continue
                # If we successfully parsed event then save it
                raw_result.append(urc)
                tag_instance_id = urc_dict["instanceId"]
                if tag_instance_id in parsed_result:
                    parsed_result[tag_instance_id].append(urc_dict)
                else:
                    parsed_result[tag_instance_id] = []
                    parsed_result[tag_instance_id].append(urc_dict)

                # TODO Actual ground truth is not same for all tags, handle that here, for now assume all at same spot.
                graph.add_tag_sample(
                    tag_instance_id,
                    urc_dict["azimuth"],
                    urc_dict["elevation"],
                    self.azimuth_angle,
                    self.tilt_angle,
                )

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
            "azimuth_gt": self.azimuth_angle,
            "elevation_gt": self.tilt_angle
        }
        return urc_dict

    def current_milli_time(self):
        return round(time.time() * 1000)
    
    def save_collected_data(self):
        for key, log in self.collected_data.items():
            with open('{}_{}.log'.format(key[0], key[1]), "w") as data_file:
                for line in log[0]:
                    data_file.write(line + '\n')

    def create_cdf(self):
        tags_errors = {}
        # gt_key is a tuple (azimuth_gt, elevation_gt)
        for gt_key, logs_from_location in self.collected_data.items():
            # For each sample in location
            for tag_id, urcs in logs_from_location[1].items():
                tags_errors[tag_id] = {
                    'azimuth_errors': list(map(lambda urc: abs(urc['azimuth'] - urc['azimuth_gt']), urcs)),
                    'elevation_errors': list(map(lambda urc: abs(urc['elevation'] - urc['elevation_gt']), urcs))
                }
            plot_num = 1
            fig = plt.figure(figsize=(12, 10))
            fig.patch.set_facecolor("#65494c")
            fig.subplots_adjust(wspace=0.09)
            plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.4)
            
            for tag_id, errors in tags_errors.items():
                plt.subplot(6,2,plot_num)
                # evaluate the histogram
                values, base = np.histogram(errors['azimuth_errors'], range=[0, max(90, np.max(errors['azimuth_errors']))])
                #evaluate the cumulative
                cumulative = np.cumsum(values)
                cdf = (np.cumsum(values)/len(errors['azimuth_errors']))
                plt.title('{} Azimuth'.format(tag_id))
                plt.axvline(x=10)
                plt.xlabel('Angle error', {'color': 'white'})
                plt.ylabel('Percent', {'color': 'white'})
                # plot the cumulative function
                plot_num = plot_num + 1
                plt.plot(base[:-1], cdf, c='blue')

                plt.subplot(6,2,plot_num)
                plt.title('{} Elevation'.format(tag_id))
                # evaluate the histogram
                values, base = np.histogram(errors['elevation_errors'], range=[0, max(90, np.max(errors['elevation_errors']))])
                #evaluate the cumulative
                cumulative = np.cumsum(values)
                cdf = (np.cumsum(values)/len(errors['elevation_errors']))
                plt.title('{} Elevation'.format(tag_id))
                plt.axvline(x=10)
                plt.xlabel('Angle error', {'color': 'white'})
                # plot the cumulative function
                plt.plot(base[:-1], cdf, c='green')
                plot_num = plot_num + 1

            plt.show()

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
    tester.collect_angles(15000, True)
    tester.rotate_antenna(45)
    tester.collect_angles(15000, True)
    tester.rotate_antenna(-90)
    tester.collect_angles(15000, True)
    tester.rotate_antenna(45) # Go back home to 0, 0
    tester.save_collected_data()
    tester.create_cdf()
    print('Finished')
