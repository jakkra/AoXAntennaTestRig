from serial_helpers import open_port, close_port, send_command_and_wait_rsp, read_line, flush_input_buffer
import numpy as np
import time


class AoAController:
    def __init__(self, port, baudrate, ctsrts, mock=False):
        self.port = port
        self.baudrate = baudrate
        self.ctsrts = ctsrts
        self.mock = mock
        self.mock_value = 0

    def start(self):
        if self.mock:
            return
        self.ser_locate = open_port(self.port, self.baudrate, self.ctsrts)

        # Turn off everything while also checking that communication is working
        self.disable_aoa()

    def enable_aoa(self):
        if not self.mock:
            return
        res = send_command_and_wait_rsp(self.ser_locate, "AT+UDFENABLE=1")
        if res == -1:
            raise Exception("Failed enabling u-connectLocate!")

    def disable_aoa(self):
        if not self.mock:
            return
        res = send_command_and_wait_rsp(self.ser_locate, "AT+UDFENABLE=1")
        if res == -1:
            raise Exception("Failed disabling u-connectLocate!")

    def flush_input_buffer(self):
        flush_input_buffer(self.ser_locate)

    def wait_for_uudf(self):
        if self.mock:
            time.sleep(0.1)
            self.mock_value = self.mock_value + 1
            return '+UUDF:F4CE5FC91A6A,-50,{},{},0,20,"CD84C98B935D","",238777,40871'.format(
                int(np.sin(self.mock_value) * 60), int(20 + np.sin(self.mock_value) * 1)
            )
        else:
            urc = read_line(self.ser_locate)
            if len(urc) > 0:
                if "+STARTUP" in urc:
                    raise Exception("Module crash detected")
                if urc.startswith("+UUDF"):
                    return urc

            return ""
