import serial
import io
import sys
import time


def open_port(port, baudrate=115200, ctsrts=0):
    try:
        return serial.Serial(port, baudrate, timeout=2, rtscts=ctsrts)
    except (serial.SerialException):
        return None


def close_port(ser):
    try:
        ser.close()
    except:
        pass


def write_line_port(ser, data):
    ser.write(data.encode() + b"\r")
    ser.flush()


def send_command_and_wait_rsp(ser, data, timeout=1):
    ser.flushInput()
    print("sending: " + data)
    write_line_port(ser, data)
    r = read_line(ser)
    now = time.time()
    while (
        now + timeout >= time.time()
        and str.find(r, "OK") < 0
        and str.find(r, "ERROR") < 0
    ):
        r = r + read_line(ser)

    if str.find(r, "OK") < 0:
        print("ERROR")
        sys.stdout.flush()
        return -1

    if now + timeout < time.time():
        return -1
    return r


def read_line(ser):
    r = ser.readline().strip()
    return r.decode("unicode_escape")
