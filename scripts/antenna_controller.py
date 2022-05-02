from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line


class AntennaController:
    def __init__(
        self,
        port,
        baudrate,
    ):
        self.port = port
        self.baudrate = baudrate

        # We assume antenna tester is homed and at 0,0
        self.azimuth_angle = 0
        self.tilt_angle = 0

    def start(self):
        self.ser_controller = open_port(self.port, self.baudrate)

    def enable_antenna_control(self):
        res = send_command_and_wait_rsp(self.ser_controller, "ENABLE=1")
        if res == -1:
            raise Exception("Failed enabling antenna!")

    def disable_antenna_control(self):
        res = send_command_and_wait_rsp(self.ser_controller, "ENABLE=0")
        if res == -1:
            raise Exception("Failed disable antenna!")

    def rotate_antenna(self, degree):
        res = send_command_and_wait_rsp(
            self.ser_controller, "AZIMUTH={}".format(degree), 10
        )
        if res == -1:
            raise Exception("Failed rotating antenna!")
        self.azimuth_angle = self.azimuth_angle + degree

    def tilt_antenna(self, degree):
        res = send_command_and_wait_rsp(
            self.ser_controller, "TILT={}".format(degree), 10
        )
        if res == -1:
            raise Exception("Failed rotating antenna!")
        self.tilt_angle = self.tilt_angle + degree

    def get_antenna_location(self):
        return (self.azimuth_angle, self.tilt_angle)

    def get_antenna_rotation(self):
        return self.azimuth_angle

    def get_antenna_tilt(self):
        return self.tilt_angle
