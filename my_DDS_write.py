import numpy as np
import time
import csv

from arduino_port import setup_arduino, open_settings, setup_arduino_port

class DDSSingleChannelWriter():
    fclk = 5e5  # see Arduino code v1.ino 
    def __init__(self, name, channel):
        '''
        Available channel: 0, 1, 2, 3
        '''

        if name == 'offline':
            self.write = lambda _, __: print('%.4f %d' % (_, __)) 
            self.write_full = lambda _, __: print('%.4f %d' % (_, __)) 
            return 

        row = open_settings(name)
        self.ser = setup_arduino(row[0])
        
        self.frequency = [DDSSingleChannelWriter.transform_frequency(float(_) * 1e3) for _ in row[1:5]]
        self.phase = [DDSSingleChannelWriter.transform_phase(float(_)) for _ in row[5:9]]
        
        self.channel = channel
        self.ser.write(b''.join(f.to_bytes(4, 'big')+p.to_bytes(2, 'big') for f, p in zip(self.frequency, self.phase)))


    @staticmethod
    def transform_phase(phi):
        if 0 <= phi <= 360:
            return round(2 ** 14 * phi / 360)
        raise RuntimeError('Phase should be inside [0,360] Deg.')

    @staticmethod
    def transform_frequency(f):
        if 0 <= f <= 250e3:
            return round(2 ** 32 * f / DDSSingleChannelWriter.fclk)
        raise RuntimeError('Frequency should be inside [0, 250] MHz')


    def write(self, new_phi):
        self.phase[self.channel] = DDSSingleChannelWriter.transform_phase(new_phi)
        self.ser.write(b''.join(f.to_bytes(4, 'big')+p.to_bytes(2, 'big') for f, p in zip(self.frequency, self.phase)))


    def write_full(self, new_freq, new_phi):
        self.frequency = [DDSSingleChannelWriter.transform_frequency(new_freq * 1000)] * 4
        self.phase[self.channel] = DDSSingleChannelWriter.transform_phase(new_phi)
        self.ser.write(b''.join(f.to_bytes(4, 'big')+p.to_bytes(2, 'big') for f, p in zip(self.frequency, self.phase)))


    def close(self):
        self.ser.close()

###################################################################################################


if __name__ == '__main__':
    DDS_writer = DDSSingleChannelWriter('master_689', 3)
    for phi in range(0, 180, 30):
        DDS_writer.write(phi)
        time.sleep(1)
        print('{} just written!'.format(phi))
    DDS_writer.close()

    x = input()
