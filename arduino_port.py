import serial
import serial.tools.list_ports
import time
import csv

class ArduinoHandShakeException(Exception):
    pass

def get_line_msg(ser):
    return ser.readline().decode('ansi')

def get_line_bin(ser):
    return ser.readline()

def which_port(iD):
    # Finds ports for user to select
    for port in serial.tools.list_ports.comports():
        if port.serial_number == iD:
            return port.device


def open_settings(device_name):
    with open('current_settings.csv') as csv_file:
        for row in csv.reader(csv_file, delimiter=','):
            if device_name == row[0]:
                return row[1:]
    raise RuntimeError('Device not found!')


class CachedPort:
    ports = {}

    def __init__(self, func) -> None:
        self.func = func

    def __call__(self, *args):
        if args[0] in CachedPort.ports:
            return CachedPort.ports[args[0]]
        CachedPort.ports[args[0]] = self.func(*args)
        return CachedPort.ports[args[0]]


@CachedPort
def setup_arduino_port(port, baud=115200, timeout=.3, max_attempts=5):
    ser = serial.Serial(port, baud, timeout=timeout)

    # Arduino will send back "Arduino setup finished!" once it's all set
    attempt = 0
    while attempt < max_attempts:
        msg = get_line_msg(ser)
        if not msg.strip():
            attempt += 1
            time.sleep(.5)
        else:
            if msg.find('Arduino') + 1:
                break
    else: 
        raise ArduinoHandShakeException('Arduino handshake failed! Did you upload v1_force-write to Arduino? ')
        
    ser.write('hello'.encode())
    attempt = 0
    while attempt < max_attempts:
        msg = get_line_msg(ser)
        if not msg.strip():
            attempt += 1
            time.sleep(.5)
        else:
            if msg.find('Arduino') + 1:
                break
    else: 
        raise ArduinoHandShakeException('Arduino handshake failed! Did you upload v1_force-write to Arduino? ')
    return ser



def setup_arduino(iD, baud=115200, timeout=.3):
    return setup_arduino_port(which_port(iD), baud, timeout)

