import matplotlib.pyplot as plt

from matplotlib.widgets import Button, TextBox, Slider
import matplotlib.lines as mlines
from matplotlib.patches import Arrow


import matplotlib as mpl

from multiprocessing import Process, Queue, freeze_support
from time import sleep
from multiprocessing import Manager
from multiprocessing.managers import BaseManager

from my_DDS_write import DDSSingleChannelWriter

font = {'family': 'serif',
        'size': 18}
mpl.rc('font', **font)
mpl.rcParams['toolbar'] = 'None'

def isint(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def setAxesFrameColor(ax, c):
    for spine in ax.spines.values():
        spine.set_edgecolor(c)


class MyButton():
    cnt = 0  
    def __init__(self, pos, text=None):
        # the matplotlib version on remote too low such that two buttons 
        # cannot overlap unless something distingushes them
        self.ax = plt.axes(pos, label=str(MyButton.cnt))
        self.button = Button(self.ax, text)
        MyButton.cnt += 1

    def setArrow(self, *args, **kwargs):
        self.ax.arrow(*args, **kwargs)

    def setAction(self, callback):
        self.button.on_clicked(callback)


class MyTextBox():
    def __init__(self, pos, text=None, *args, **kwargs):
        self.ax = plt.axes(pos)
        self.tb = TextBox(self.ax, text, *args, **kwargs)
        self.valid = True

        self.tb.on_submit(self.textbox_callback)
        self.val = kwargs['initial']

    def textbox_callback(self, event):
        if not isint(event):
            setAxesFrameColor(self.ax, 'red')
        else:
            setAxesFrameColor(self.ax, 'k')
            self.val = int(event)
            self.tb.set_val(self.val)

class MySlider():
    def __init__(self, pos, *args, **kwargs):
        self.ax = plt.axes(pos)
        self.pos = self.ax.get_position()
        self.slider = Slider(self.ax, *args, **kwargs)

    def addAnnotate(self, *args, **kwargs):
        self.ax.annotate(*args, **kwargs)

    def inAxis(self, x, y):
        return(self.pos.xmin < x < self.pos.xmax and self.pos.ymin < y < self.pos.ymax)

class Sweeper():
    def __init__(self, writer):
        self.cmd_queue = Queue()
        self.ret_queue = Queue()
        self.background = Process(target=Sweeper.backend, args=(writer, self.cmd_queue,self.ret_queue))
        self.background.start()


    @staticmethod
    def backend(writer, q, q_ret):
        while True:
            if not q.empty():
                cmd, args = q.get()
                if cmd == 'run':
                    for ph in range(*args):
                        writer.write(ph)
                        q_ret.put(ph)
                        if not q.empty():
                            q_ret.put(-1)
                            break
                    q_ret.put(-1)
                if cmd == 'quit':
                    return
            sleep(.1)



class DDSSingleChannelBack:
    def __init__(self, writer, init_phase=0, fine_step=1, range_init=None):
        if not range_init:
            range_init = (0, 180, 10)

        self.draw(range_init)

        self.cur_phase = 0
        self.fine_step = fine_step

        self.up.button.on_clicked(self.up_callback)
        self.down.button.on_clicked(self.down_callback)

        self.sweep.button.on_clicked(self.sweep_on_click)
        self.stop.button.on_clicked(self.stop_on_click)

        self.sl.slider.on_changed(self.slider_on_change)

        manager = BaseManager()
        manager.start()
        self.writer = writer
        self.write_DDS = self.writer.write



    def draw(self, range_init):
        # basic setup
        self.fig = plt.figure(figsize=(6, 6))
        self.fig.canvas.mpl_disconnect(
            self.fig.canvas.manager.key_press_handler_id)  # remove hotkeys

        # drawing in background
        background = plt.axes([0, 0, 1, 1])

        half = 0.5
        fine_offset_x = -.05
        fine_offset_y = -0.02

        button_size = 0.25
        button_offset_x = .2
        button_offset_y = .1

        text_bar_y = (half + button_offset_y +
                      button_size + 1) / 2. + fine_offset_y
        background.annotate(
            'Fine', (half + button_offset_x + fine_offset_x, text_bar_y))

        coarse_offset_x = .15
        background.annotate('Coarse', (coarse_offset_x, text_bar_y))

        vert_line_offset_x = .1
        background.add_line(mlines.Line2D(
            [half+vert_line_offset_x] * 2, [.1, .9], c='k', lw=1, alpha=.6))

        self.state_banner = background.annotate('', (.15, .06))

        # Buttons for fine tuning
        self.up = MyButton([half + button_offset_x, half +
                            button_offset_y, button_size, button_size])
        self.up.setArrow(0, 0, 0, 1, head_length=0.6)

        self.down = MyButton([half + button_offset_x, half -
                              button_offset_y - button_size, button_size, button_size])
        self.down.setArrow(0, 0, 0, -1, head_length=0.6)

        # Coarse tuning
        textbox_height = .1
        textbox_width = .3
        textbox_offset_x = -fine_offset_x
        textbox_padding = .05

        self.tb_start = MyTextBox([coarse_offset_x + textbox_offset_x, text_bar_y -
                                   textbox_padding - textbox_height, textbox_width, textbox_height], 'Start ', initial=range_init[0])
        self.tb_end = MyTextBox([coarse_offset_x + textbox_offset_x, text_bar_y -
                                 2 * textbox_padding - 2*textbox_height, textbox_width, textbox_height], 'End ', initial=range_init[1])
        self.tb_step = MyTextBox([coarse_offset_x + textbox_offset_x, text_bar_y -
                                  3 * textbox_padding - 3 * textbox_height, textbox_width, textbox_height], 'Step ', initial=range_init[2])

        sweep_width = .2
        sweep_height = .08
        self.sweep = MyButton([coarse_offset_x + textbox_offset_x / 2., text_bar_y -
                               4 * textbox_padding - 4 * textbox_height, sweep_width, sweep_height], 'Sweep')
        self.stop = MyButton([coarse_offset_x + textbox_offset_x / 2., text_bar_y -
                               4 * textbox_padding - 4 * textbox_height, sweep_width, sweep_height], 'Stop')
        self.stop.ax.set_visible(False)

        # Hand tuning
        slider_x = .08
        slider_y = .15
        slider_width = .4
        slider_height = .05

        self.sl = MySlider([slider_x, slider_y, slider_width,
                           slider_height], '', 0, 360, valfmt=' %d')
        self.sl.addAnnotate('Phase', (.5, 1.15), annotation_clip=False)

    def up_callback(self, event):
        self.cur_phase += 1
        self.write_DDS(self.cur_phase)
        self.update_slider()

    def down_callback(self, event):
        self.cur_phase -= 1
        self.write_DDS(self.cur_phase)
        self.update_slider()

    def slider_on_change(self, event):
        self.cur_phase = self.sl.slider.val
        self.write_DDS(self.cur_phase)


    def sweep_on_click(self, event):
        if self.tb_start.valid and self.tb_end.valid and self.tb_step.valid:
            self.sweep.ax.set_visible(False)
            self.stop.ax.set_visible(True)

            plt.pause(.1)

            self.sweeper = Sweeper(self.writer)
            self.sweeper.cmd_queue.put(('run', (self.tb_start.val, self.tb_end.val, self.tb_step.val)))

            while True:
                if not self.sweeper.ret_queue.empty():
                    ph = self.sweeper.ret_queue.get()
                    if ph == -1:
                        break
                    self.cur_phase = ph
                    self.update_slider()
                    plt.pause(.5)
                sleep(.1)

            self.stop.ax.set_visible(False)
            self.sweep.ax.set_visible(True)
            self.sweeper.cmd_queue.put(('quit', ()))
        else:
            print('Invalid argument')

    def stop_on_click(self, event):
        self.stop.ax.set_visible(False)
        self.sweep.ax.set_visible(True)

        self.sweeper.cmd_queue.put(('quit', ()))
        plt.pause(.1)

    def update_slider(self):
        self.sl.slider.set_val(self.cur_phase)

    def update_banner(self, text):
        self.state_banner.set_text(text)

    def launch(self):
        plt.show()
        print('Current phase %.3f' % (self.cur_phase))
        input('Terminating program... \nIf you want to upload permanantly the DDS params, be sure to update current_settings.csv, upload v1.ino, and run write_DDS.py\n')
        


if __name__ == '__main__':
    BaseManager.register('DDS_writer', DDSSingleChannelWriter)
    writer = manager.DDS_writer('master_689', 3)
    freeze_support()
    DDSSingleChannelBack(writer).launch()
