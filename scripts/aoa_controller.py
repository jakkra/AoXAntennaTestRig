from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line


class AoAController:
    def __init__(
        self,
        port,
        baudrate,
        ctsrts,
    ):
        self.port = port
        self.baudrate = baudrate
        self.ctsrts = ctsrts

    def start(self):
        self.ser_locate = open_port(self.port, self.baudrate, self.ctsrts)

        # Turn off everything while also checking that communication is working
        self.disable_aoa()

    def enable_aoa(self):
        res = send_command_and_wait_rsp(self.ser_locate, "AT+UDFENABLE=1")
        if res == -1:
            raise Exception("Failed enabling u-connectLocate!")

    def disable_aoa(self):
        res = send_command_and_wait_rsp(self.ser_locate, "AT+UDFENABLE=0")
        if res == -1:
            raise Exception("Failed disabling u-connectLocate!")

    def wait_for_uudf(self):
        urc = read_line(self.ser_locate)
        if len(urc) > 0:
            if "+STARTUP" in urc:
                raise Exception("Module crash detected")
            if urc.startswith("+UUDF"):
                return urc

        return ""
