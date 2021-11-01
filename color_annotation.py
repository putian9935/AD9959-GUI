
import matplotlib.pyplot as plt

from matplotlib.widgets import TextBox
from matplotlib import transforms
from math import log10, ceil


def step2digit(step):
    """
    Find the most significant digit of 0 < step < 1. 

    e.g. step = 0.025 return 2
    """
    return ceil(log10(1./step))


class ColorTextBox(TextBox):
    """
    ColorTextBox 

    Two strings:
    1. text_disp: inherent, editable 
    2. rendered_texts: what is shown when not editting
    """

    def __init__(self, highlight_digit=2, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_disp.set_visible(False)
        self.highlight_digit = highlight_digit

        text = '%.4f' % kwargs['initial']
        self.text_disp.set_text(text)
        self.rendered_texts = []
        self._update_highlight_position(self._chop_float(text))

    def _update_highlight_position(self, chopped_strings):
        if len(self.rendered_texts):
            for t in self.rendered_texts:
                t.set_visible(False)
        self.rendered_texts = []

        # hack from https://stackoverflow.com/questions/9169052/partial-coloring-of-text-in-matplotlib
        t = self.ax.transData
        fig = plt.gcf()

        for s, c in zip(chopped_strings, "krk"):
            text = plt.text(self.DIST_FROM_LEFT, 0.5, s, color=c, transform=t,
                            verticalalignment='center', horizontalalignment='left')
            text.draw(fig.canvas.get_renderer())
            ex = text.get_window_extent()
            t = transforms.offset_copy(
                text._transform, x=ex.width, units='dots')
            self.rendered_texts.append(text)
        plt.draw()

    def _chop_float(self, str_val):
        """
        Chop a float-string into 3 pieces, one is highlight digits. str_val is generated with '%.4f'

        Say val = 58.7830, highlight_digit = 2; 
        then this function returns ["58.7", "8", "30"]
        """
        if self.highlight_digit < 4:
            return [str_val[:-(4-self.highlight_digit)-1], str_val[-(4-self.highlight_digit)-1], str_val[-(4-self.highlight_digit):]]
        else: 
            return [str_val[:-(4-self.highlight_digit)-1], str_val[-(4-self.highlight_digit)-1]]

    def set_val(self, val):
        super().set_val(val)

        text = '%.4f' % val
        self.text_disp.set_text(text)
        # for the correct cursor position
        self.cursor_index = min(self.cursor_index, len(text))

        for i, s in enumerate(self._chop_float(text)):
            self.rendered_texts[i].set_text(s)

        self._rendercursor()  # otherwise position is wrong
        plt.draw()

    def _submit_action(self, event):
        self.set_val(float(event))

    def _click(self, event):
        if event.inaxes == self.ax:
            self.text_disp.set_visible(True)
            for t in self.rendered_texts:
                t.set_visible(False)
        else:
            self.text_disp.set_visible(False)
            for t in self.rendered_texts:
                t.set_visible(True)
        super()._click(event)


class MyColorTextBox():
    def __init__(self, pos, highlight_digit, *args, **kwargs):
        self.ax = plt.axes(pos)
        self.tb = ColorTextBox(highlight_digit, self.ax,
                               label=None, *args, **kwargs)

    def addAnnotate(self, *args, **kwargs):
        self.ax.annotate(*args, **kwargs)


if __name__ == '__main__':
    import matplotlib as mpl

    font = {'family': 'serif',
            'size': 16}
    mpl.rc('font', **font)
    mpl.rcParams['toolbar'] = 'None'

    fig = plt.figure(figsize=(8, 6))

    tb_freq_x = .08
    tb_freq_y = .6
    tb_freq_width = .4
    tb_freq_height = .1
    tb_freq = MyColorTextBox([tb_freq_x, tb_freq_y, tb_freq_width,
                              tb_freq_height], 2, initial=57.6872)
    tb_freq.addAnnotate('Freq. (MHz)', (0, 1.15), annotation_clip=False)
    tb_freq.tb.on_submit(tb_freq.tb._submit_action)
    plt.show()
