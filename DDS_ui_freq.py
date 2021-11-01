import matplotlib.pyplot as plt

from matplotlib.widgets import Button, TextBox, Slider, CheckButtons
import matplotlib.lines as mlines
from matplotlib.patches import Arrow
from color_annotation import MyColorTextBox, step2digit

import matplotlib as mpl


from time import sleep


from my_DDS_write import DDSSingleChannelWriter

font = {'family': 'serif',
        'size': 16}
mpl.rc('font', **font)
mpl.rcParams['toolbar'] = 'None'

def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def setAxesFrameColor(ax, c):
    for spine in ax.spines.values():
        spine.set_edgecolor(c)

def turnOffAxesFrame(ax):
    for spine in ax.spines.values():
        spine.set_visible(False)


class MyButton():
    def __init__(self, pos, text=None):
        self.ax = plt.axes(pos)
        self.button = Button(self.ax, text)

    def setArrow(self, *args, **kwargs):
        self.ax.arrow(*args, **kwargs)

    def setAction(self, callback):
        self.button.on_clicked(callback)


class MyCheckButtons():
    def __init__(self, pos, labels):
        mpl.rcParams.update({'font.size': 14})
        self.ax = plt.axes(pos, facecolor=None, alpha=0)
        self.cbutton = CheckButtons(self.ax, labels)
        self.cbutton.set_active(0)

        # artistic aspect
        mpl.rcParams.update({'font.size': 16})
        self.ax.patch.set_alpha(0)
        turnOffAxesFrame(self.ax)

    def setArrow(self, *args, **kwargs):
        self.ax.arrow(*args, **kwargs)

    def setAction(self, callback):
        self.cbutton.on_clicked(callback)




class MySlider():
    def __init__(self, pos, *args, **kwargs):
        self.ax = plt.axes(pos)
        self.pos = self.ax.get_position()
        self.slider = Slider(self.ax, *args, **kwargs)

    def addAnnotate(self, *args, **kwargs):
        self.ax.annotate(*args, **kwargs)

    def inAxis(self, x, y):
        return(self.pos.xmin < x < self.pos.xmax and self.pos.ymin < y < self.pos.ymax)



class DDSSingleChannelBack:
    def __init__(self, writer, init_phase=0, fine_step=None, freq_init=None):
        if not freq_init:
            freq_init = 57.6
        if not fine_step:
            fine_step = (.01, 1)  # (freq., phase) pair

        self.fine_step = fine_step
        self.draw(freq_init)

        self.cur_freq = freq_init
        self.cur_phase = 0
        self.fine_type = 0  # 0 for frequency

        self.up.button.on_clicked(self.up_callback)
        self.down.button.on_clicked(self.down_callback)

        self.sl.slider.on_changed(self.slider_on_change)
        self.select.cbutton.on_clicked(self.select_callback)
        self.tb_freq.tb.on_submit(self.textbox_on_submit)

        self.writer = writer
        self.write_DDS = self.writer.write_full



    def draw(self, freq_init):
        # basic setup
        self.fig = plt.figure(figsize=(6, 4))
        self.fig.canvas.mpl_disconnect(
            self.fig.canvas.manager.key_press_handler_id)  # remove hotkeys

        # drawing in background
        background = plt.axes([0, 0, 1, 1])

        half = 0.5
        fine_offset_x = -.05
        fine_offset_y = -0.02

        button_size = 0.25
        button_offset_x = .2
        button_offset_y = .05

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
                            button_offset_y, button_size * 3 / 4, button_size])
        self.up.setArrow(0, 0, 0, 1, head_length=0.6)

        self.down = MyButton([half + button_offset_x, half -
                              button_offset_y - button_size, button_size  * 3 / 4, button_size])
        self.down.setArrow(0, 0, 0, -1, head_length=0.6)

        select_width = .15
        select_height = .2
        self.select = MyCheckButtons([half + button_offset_x + fine_offset_x + button_size / 2., text_bar_y - select_height / 2., select_width, select_height], ['Freq', 'Phase'])


        # Hand tuning
        slider_x = .08
        slider_y = .3
        slider_width = .4
        slider_height = .1

        self.sl = MySlider([slider_x, slider_y, slider_width,
                           slider_height], '', 0, 360, valfmt=' %d')
        self.sl.addAnnotate('Phase', (.5, 1.15), annotation_clip=False)

        # Type freq
        tb_freq_x = .08
        tb_freq_y = .6
        tb_freq_width = .4
        tb_freq_height = .1
        self.tb_freq = MyColorTextBox([tb_freq_x, tb_freq_y, tb_freq_width,
                        tb_freq_height], step2digit(self.fine_step[0]), initial=freq_init)
        self.tb_freq.addAnnotate('Freq. (MHz)', (0, 1.15), annotation_clip=False)
        


    def up_callback(self, event):
        if self.fine_type:
            self.cur_phase += self.fine_step[self.fine_type]

            # when slider is changed, the slider_on_changed is called automatically 
            # the same applies to other button
            # self.write_DDS(self.cur_freq, self.cur_phase)
            self.update_slider()
        else:
            self.cur_freq += self.fine_step[self.fine_type]
            # when textbox is changed, the slider_on_submit is called automatically 
            # the same applies to other button
            # self.write_DDS(self.cur_freq, self.cur_phase)
            self.update_tb()


    def down_callback(self, event):
        if self.fine_type:
            self.cur_phase -= self.fine_step[self.fine_type]
            self.update_slider()
        else:
            self.cur_freq -= self.fine_step[self.fine_type]
            self.update_tb()

    def slider_on_change(self, event):
        # on some version of matplotlib, slider.val returns numpy.float64, which causes trouble
        self.cur_phase = float(self.sl.slider.val)  
        self.write_DDS(self.cur_freq, self.cur_phase)

    def select_callback(self, event):
        index = 0 if event[0] == 'F' else 1
        self.fine_type = index

        # whatever clicked, the on/off of it gets changed
        if self.select.cbutton.lines[index][0].get_visible():
            index = 1 - index
        for l in self.select.cbutton.lines[index]:
            l.set_visible(not l.get_visible())



    def textbox_on_submit(self, event):
        if not isfloat(event):
            setAxesFrameColor(self.tb_freq.tb.ax, 'red')
        else:
            setAxesFrameColor(self.tb_freq.tb.ax, 'k')
            self.cur_freq = float(event)
            self.write_DDS(self.cur_freq, self.cur_phase)
            self.update_tb()

    def update_slider(self):
        self.sl.slider.set_val(self.cur_phase)

    def update_banner(self, text):
        self.state_banner.set_text(text)

    def update_tb(self):
        self.tb_freq.tb.set_val(self.cur_freq)

    def launch(self):
        plt.show()
        print('Current freq. %.3f' % (self.cur_freq))
        print('Current phase %.3f' % (self.cur_phase))
        input('Terminating program... \nIf you want to upload permanantly the DDS params, be sure to update current_settings.csv, upload v1.ino, and run write_DDS.py\n')


if __name__ == '__main__':
    DDSSingleChannelBack(DDSSingleChannelWriter('offline', 3)).launch()
