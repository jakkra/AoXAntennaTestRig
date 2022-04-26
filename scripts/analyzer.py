import argparse, sys, time
from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line
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
                    urc_dict["angleH"],
                    urc_dict["angleV"],
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
            "angleH": int(urc_params[2]),
            "angleV": int(urc_params[3]),
            "rssi2": int(urc_params[4]),
            "channel": int(urc_params[5]),
            "anchor_id": urc_params[6].replace('"', ""),
            "user_defined_str": urc_params[7].replace('"', ""),
            "timestamp_ms": int(urc_params[8]),
        }
        return urc_dict

    def current_milli_time(self):
        return round(time.time() * 1000)


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
