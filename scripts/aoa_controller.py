from serial_helpers import (
    open_port,
    close_port,
    send_command_and_wait_rsp,
    read_line,
    flush_input_buffer,
)
import numpy as np
import time
import json
import base64


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
        if self.mock:
            return
        flush_input_buffer(self.ser_locate)

    def wait_for_aoa_event(self):
        if self.mock:
            time.sleep(0.1)
            self.mock_value = self.mock_value + 1
            line = '+UUDF:F4CE5FC91A6A,-50,{},{},0,20,"CD84C98B935D","",238777,40871'.format(
                int(np.sin(self.mock_value) * 60), int(20 + np.sin(self.mock_value) * 1)
            )
            return (line, self.parse_uudf(line))
        else:
            try:
                line = read_line(self.ser_locate)
                if len(line) > 0:
                    if "+STARTUP" in line:
                        raise Exception("Module crash detected")
                    return (line, self.parse_event(line))
            except Exception as e:
                print(e)
                return ("", None)

            return ("", None)

    def parse_event(self, line):
        if line.startswith("+UUDF"):
            return self.parse_uudf(line)
        if line.startswith('{"id"'):  # Raw IQ debug mode format
            return self.parse_debug_json(line)

    def parse_uudf(self, urc_str):
        splitted = urc_str.find(":")

        urc, r = urc_str[:splitted], urc_str[splitted:]
        if urc.upper() != "+UUDF":
            return None

        urc_params = r.split(",")
        instanceId = urc_params[0][1:]
        if len(instanceId) != 12:
            return None

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

    def parse_debug_json(self, dbg_json):
        dbg_evt = json.loads(dbg_json)
        instanceId = dbg_evt["id"].replace('"', "")
        if len(instanceId) != 12:
            return None
        urc_dict = {
            "instanceId": dbg_evt["id"],
            "rssi": int(dbg_evt["rssi"]),
            "azimuth": round(float(dbg_evt["est"][0])),
            "elevation": round(float(dbg_evt["est"][1])),
            "azimuth_raw": round(float(dbg_evt["est_raw"][0])),
            "elevation_raw": round(float(dbg_evt["est_raw"][1])),
            "rssi2": 0,  # N/A for now
            "channel": int(dbg_evt["ch"]),
            "anchor_id": dbg_evt["a_id"].replace('"', ""),
            "user_defined_str": "",
            "timestamp_ms": int(dbg_evt["ms"]),
            "iqs": self.parse_iqs(dbg_evt["iq_b64"]),
        }
        return urc_dict

    def parse_iqs(self, iq_b64):
        decoded = base64.b64decode(iq_b64)
        decoded = list(
            map(lambda val: str(val if val < 127 else (256 - val) * (-1)), decoded)
        )
        # Make sure we got correct amount of I+Qs. 82 samples, I+Q for each sample.
        if len(decoded) != 82 * 2:
            raise Exception("Wrong amount of IQs")
        decoded = ",".join(decoded)
        return decoded
