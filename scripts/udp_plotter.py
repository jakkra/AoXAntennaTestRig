import tkinter as tk
import time, sys, argparse
import socket
from live_plot_anchor import LivePlotAnchor
from analyzer import AoATester
import traceback

class UDPPlotter:
    def __init__(self, ip, port, tag_id, max_anchors):
        localIP = str(ip)
        localPort = int(port)
        self.tracked_tag_id = tag_id
        self.bufferSize  = 1024
        self.UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.UDPServerSocket.bind((localIP, localPort))
        self.live_plot = LivePlotAnchor(max_anchors)
        self.raw_result = []

    def run(self):
        tracked_tag = None
        while(True):
            bytesAddressPair = self.UDPServerSocket.recvfrom(self.bufferSize)
            message = bytesAddressPair[0]
            address = bytesAddressPair[1]
            clientMsg = "{}: {}".format(address, message)
            print(clientMsg)
            try:
                urc = message
                urc = urc.decode("utf-8")

                urc_dict = self.parse_uudf(urc)
                if urc_dict != None:
                    self.raw_result.append(urc)
                    tag_id = urc_dict["instanceId"]
                    anchor_id = urc_dict["anchor_id"]
                    if tracked_tag == None:
                        tracked_tag = tag_id
                        self.live_plot.set_title("Tracked tag: {}".format(tracked_tag))

                    if (self.tracked_tag_id is not None and self.tracked_tag_id != tag_id):
                        continue

                    self.live_plot.add_anchor_sample(
                        anchor_id,
                        #tag_id,
                        urc_dict["azimuth"],
                        urc_dict["elevation"]
                    )
            except Exception as e:
                print(traceback.format_exc())
                pass

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



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Angle plotter over UDP")

    parser.add_argument('--ip', dest='ip', required=False, default='0.0.0.0', help='The local IP address UDP angles are sent to.')
    parser.add_argument("--port", dest="port", required=False, default=54444, help='The port UDP angles are sent to.')
    parser.add_argument('--tagId', dest='tag_id', required=False, default=None, help='Only plot angles from this specific tag.')
    parser.add_argument('--max_anchors', dest='max_anchors', required=False, default=6, help='Adjusts the plot size to fit this number of anchors, default 6.')

    args = parser.parse_args()

    print('Setting up UDP server on {0}, {1}'.format(args.ip, args.port),  args.tag_id)

    localIP = str(args.ip)
    localPort = int(args.port)

    plotter = UDPPlotter(localIP, localPort, args.tag_id, int(args.max_anchors))
    plotter.run()