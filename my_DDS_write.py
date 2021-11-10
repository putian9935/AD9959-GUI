import numpy as np
import time
import csv

from arduino_port import setup_arduino, open_settings, setup_arduino_port, get_line_bin
from collections import Iterable

def counted_func(prefix=None):
    def inner(f):
        cnt = 0

        def ret(*args, **kwargs):
            nonlocal cnt
            cnt += 1
            print('%s[%d]\t' % (prefix, cnt), end='')
            f(*args, **kwargs)

        return ret
    return inner


def show_channel_parameter(bin_str):
    print('%-4s %-8s %-4s' % ('Ch.', 'Freq.', 'Phase'))
    for ch in range(4):
        print('%-4d %-8d %-4.1f' % (
            ch,
            DDSSingleChannelWriter.inverse_transform_frequency(int().from_bytes(
                bin_str[6*ch:6*ch+4], 'big') / 1000),  # in the unit of MHz
            DDSSingleChannelWriter.inverse_transform_phase(int().from_bytes(bin_str[6*ch+4:6*ch+6], 'big')))
        )


class Command():
    UPDATE = 0
    UPLOAD = 1
    DNLOAD = 2
    EXIT  = 3


class DDSSingleChannelWriter():
    fclk = 500000  # see Arduino code v1.ino

    def __init__(self, name, channel, shared_channels=None):
        '''
        Available channel: 0, 1, 2, 3
        '''

        
        row = open_settings(name)
        self.header = '%s, %s, '%(name, row[0])
        self.frequency = []
        self.phase = []
        self.frequency = [DDSSingleChannelWriter.transform_frequency(
            float(_) * 1e3) for _ in row[1:5]]
        self.phase = [DDSSingleChannelWriter.transform_phase(
            float(_)) for _ in row[5:9]]

        self.channel = channel
        if shared_channels is None: 
            shared_channels = [self.channel]
        elif isinstance(shared_channels, int):
            shared_channels = [self.channel, shared_channels] 
        elif isinstance(shared_channels, Iterable):
            shared_channels = [self.channel] + [ch for ch in shared_channels]
        self._calculate_commands(shared_channels)

        if name == 'offline':
            self.write = lambda _: print('%.4f %d' % (_))
            self.write_full = lambda _, __: print('%.4f %d' % (_, __))
            self.upload = lambda *_: print('Uploaded to EEPROM!')
            self.download = lambda *_: print('Downloading...')
            return
        
        self.ser = setup_arduino(row[0])

        # update all channels, otherwise some may not be able to open 
        self.ser.write((15 << 4).to_bytes(1,'big')+b''.join(f.to_bytes(4, 'big') +
                       p.to_bytes(2, 'big') for f, p in zip(self.frequency, self.phase)))
        get_line_bin(self.ser)
        

    @staticmethod
    def transform_phase(phi):
        if 0 <= phi <= 360:
            return round(2 ** 14 / 360 * phi)
        raise RuntimeError('Phase should be inside [0,360] Deg.')

    @staticmethod
    def transform_frequency(f):
        if 0 <= f <= 250e3:
            return round(2 ** 32 / DDSSingleChannelWriter.fclk * f)
        raise RuntimeError('Frequency should be inside [0, 250] MHz')

    @staticmethod
    def inverse_transform_phase(transformed_phi):
        return transformed_phi * (360 / 2 ** 14)

    @staticmethod
    def inverse_transform_frequency(transformed_f):
        return transformed_f * (DDSSingleChannelWriter.fclk / 2 ** 32)

    @counted_func('Update')
    def write(self, new_phi):
        print('%d' % (new_phi))
        self.phase[self.channel] = DDSSingleChannelWriter.transform_phase(
            new_phi)
        self.ser.write(self.commands[Command.UPDATE]+b''.join(f.to_bytes(4, 'big') +
                       p.to_bytes(2, 'big') for f, p in zip(self.frequency, self.phase)))

        if self.ser.inWaiting:
            get_line_bin(self.ser)
            print('%d' % (new_phi))

    @counted_func('Update')
    def write_full(self, new_freq, new_phi):
        self.frequency = [
            DDSSingleChannelWriter.transform_frequency(new_freq * 1000)] * 4
        self.phase[self.channel] = DDSSingleChannelWriter.transform_phase(
            new_phi)
        self.ser.write(self.commands[Command.UPDATE]+b''.join(f.to_bytes(4, 'big') +
                       p.to_bytes(2, 'big') for f, p in zip(self.frequency, self.phase)))

        if self.ser.inWaiting:
            get_line_bin(self.ser)
            print('%.4f %d' % (new_freq, new_phi))

    @counted_func('Upload')
    def upload(self):
        self.ser.write(self.commands[Command.UPLOAD]+b''.join(f.to_bytes(4, 'big') +
                       p.to_bytes(2, 'big') for f, p in zip(self.frequency, self.phase)))
        if self.ser.inWaiting:
            get_line_bin(self.ser)
            print('Uploaded to EEPROM! ')

    @counted_func('Dnload')
    def download(self):
        print('Downloading...')
        self.ser.write(self.commands[Command.DNLOAD]+b'\x00'*24)
        if self.ser.inWaiting:
            show_channel_parameter(get_line_bin(self.ser))
    
    def _calculate_commands(self, sc):
        def bit_xor(a, b):
            return bytes(_ ^ __ for _, __ in zip(a, b)) 
        
        b_ch_en = sum(16 << ch for ch in sc).to_bytes(1, 'big')
        self.commands = tuple(bit_xor(b_ch_en, cmd.to_bytes(1, 'big')) for cmd in range(4))

    def send_self_check(self):
        self.ser.write(Command.EXIT+b'\x00'*24)

    # Not in use
    def close(self):
        self.ser.close()

###################################################################################################


if __name__ == '__main__':
    print(DDSSingleChannelWriter.transform_frequency(250e3))
    print(DDSSingleChannelWriter.transform_frequency(250e3).to_bytes(4, 'big'))
    print(SpecialCommand.UPLOAD)
    print(SpecialCommand.UPLOAD.to_bytes(4, 'big'))
    exit()
    DDS_writer = DDSSingleChannelWriter('master_689', 3)
    for phi in range(0, 180, 30):
        DDS_writer.write(phi)
        time.sleep(1)
        print('{} just written!'.format(phi))
    DDS_writer.close()

    x = input()
