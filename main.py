# -*- coding: utf-8 -*-

import sys

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import \
    NavigationToolbar2QT as NavigationToolbar2
from PyQt5 import QtCore, QtGui, QtWidgets

import mainwindow
import pogruzhatel_jit

matplotlib.use('Qt5Agg')


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None):
        self.fig, self.axarr = plt.subplots(4, sharex=True)
        self.labels_enable()
        self.fig.subplots_adjust(
            left=.1,
            bottom=.05,
            right=.96,
            top=.96,
            hspace=0.3,
        )
        self.grid_enable()
        super(MplCanvas, self).__init__(self.fig)

    def grid_enable(self):
        for x in self.axarr:
            x.grid(True)

    def labels_enable(self):
        self.axarr[0].set_title(r'$x(t)$ - глубина погружения, м')
        self.axarr[1].set_title(r'$\omega$ - количество оборотов в секунду')
        self.axarr[2].set_title(r'$\Sigma$ - импульс')
        self.axarr[3].set_title(r'$\Sigma$ - импульс с шумом')


# Class main form
class xolm(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.start_button.clicked.connect(self.start_draw)
        self.stop_button.clicked.connect(self.stop_draw)

        float_validator = QtGui.QDoubleValidator(0.0, 5.0, 2)
        int_validator = QtGui.QIntValidator(0, 10)
        float_validator.setLocale(QtCore.QLocale(QtCore.QLocale.English))

        for widget in (self.time_step_edit,
                       self.pile_length_edit,
                       self.pile_width_edit,
                       self.pile_depth_edit,
                       self.plunger_weight_edit,
                       self.coef_lower_pile_edit,
                       self.coef_soil_pile_edit,
                       self.resistance_surface_edit):
            widget.textChanged.connect(self.param_change)
            widget.setValidator(float_validator)

        for widget in (self.plunger_pairs_edit,):
            widget.textChanged.connect(self.param_change)
            widget.setValidator(int_validator)

        self.speed_slider.valueChanged.connect(self.speed_boost)

        self.sc = MplCanvas(self)
        self.draw_box_layout.addWidget(self.sc)
        self.draw_box_layout.addWidget(NavigationToolbar2(self.sc, self))

        self.started_status = 'STOP'

        self.timer = QtCore.QTimer()
        self.timer_ms = 100
        self.timer.timeout.connect(self.draw_line)

        self.last_x = 0
        self.last_t = 0
        self.last_w = 0
        self.last_impulse = 0
        self.last_impulse_noise = 0
        self.last_cut_w = 0

        self.param_change(True)

        self.default_line_step = 0
        self.dynamic_line_step = 0

    def speed_boost(self, s):
        self.dynamic_line_step = self.default_line_step * s

    def draw_line(self):
        cut_t = self.t[self.last_t:self.last_t + self.dynamic_line_step + 1]
        cut_x = self.x[self.last_x:self.last_x + self.dynamic_line_step + 1]
        cut_w = self.w[self.last_w:self.last_w + self.dynamic_line_step + 1]
        cut_impulse = self.impulse[self.last_impulse:self.last_impulse + self.dynamic_line_step + 1]
        cut_impulse_noise = self.impulse_noise[self.last_impulse_noise:self.last_impulse_noise + self.dynamic_line_step + 1]
        if cut_t:
            self.sc.axarr[0].plot(cut_t, cut_x, linewidth=2, color='r')
            self.sc.axarr[1].plot(cut_t, cut_w, linewidth=2, color='g')
            self.sc.axarr[2].plot(cut_t, cut_impulse, linewidth=2, color='b')
            self.sc.axarr[3].plot(cut_t, cut_impulse_noise, linewidth=2, color='m')
            self.last_x += self.dynamic_line_step
            self.last_t += self.dynamic_line_step
            self.last_w += self.dynamic_line_step
            self.last_impulse += self.dynamic_line_step
            self.last_impulse_noise += self.dynamic_line_step
            self.last_cut_w += self.dynamic_line_step
            self.time_edit.setText(str(round(cut_t[-1], 2)))
            self.depth_edit.setText(str(round(cut_x[-1], 2)))
            self.speed_edit.setText(str(round(cut_w[-1], 2)))
            self.impulse_edit.setText(str(round(cut_impulse[-1], 2)))
            self.impulse_noise_edit.setText(str(round(cut_impulse_noise[-1], 2)))
            self.sc.fig.canvas.draw()
        else:
            self.timer.stop()

    def scan_param(self):
        self.g = 9.81
        self.n = int(self.plunger_pairs_edit.text())  # количество пар дебалансов
        self.dt = float(self.time_step_edit.text())  # шаг по времени
        self.l = float(self.pile_length_edit.text())  # длина сваи (м)
        self.width_pipe = float(self.pile_width_edit.text())
        self.depth_pipe = float(self.pile_depth_edit.text())
        self.pile_perimeter = self.width_pipe * 2 + self.depth_pipe * 2  # периметр основания сваи (м)
        self.pile_area = self.width_pipe * self.depth_pipe  # площадь основания сваи (м^2)
        self.plunger_weight = float(self.plunger_weight_edit.text())  # вес погружателя
        self.pile_weight = self.l * 3.14 * 4  # (3.14 - плотность)
        self.M = self.plunger_weight + self.pile_weight  # вес машинки + сваи (кг)
        self.gamma_cr = float(self.coef_lower_pile_edit.text())  # коэффициент условий работы грунта под нижним концом сваи
        self.gamma_cf = float(self.coef_soil_pile_edit.text())  # коэффициент условий работы грунта на боковой поверхности
        self.fi = float(self.resistance_surface_edit.text())  # расчётное сопротивлене по боковой поверхности (кПа)

    def param_change(self, s):
        if s:
            self.scan_param()
            self.pile_weight_edit.setText(str(self.pile_weight))  # Вес сваи, кг.
            self.pile_perimeter_edit.setText(str(self.pile_perimeter))  # Периметр сваи, м.
            self.pile_area_edit.setText(str(self.pile_area))  # Площадь основания сваи, кв. м.
        else:
            self.sender().setText('0')

    def start_draw(self):
        if self.started_status == 'START':
            self.timer.stop()
            self.started_status = 'PAUSE'
            self.start_button.setText('Старт')
        elif self.started_status == 'STOP':
            self.started_status = 'START'
            self.start_button.setText('Пауза')
            self.sc.axarr[0].clear()
            self.sc.axarr[1].clear()
            self.sc.axarr[2].clear()
            self.sc.axarr[3].clear()
            self.sc.labels_enable()
            self.sc.grid_enable()
            self.scan_param()
            self.x, self.t, self.w, self.impulse, self.impulse_noise = pogruzhatel_jit.main(
                self.g,
                self.n,
                self.dt,
                self.l,
                self.pile_perimeter,
                self.pile_area,
                self.M,
                self.gamma_cr,
                self.gamma_cf,
                self.fi
            )
            self.default_line_step = len(self.x) // 3000
            self.dynamic_line_step = self.default_line_step * self.speed_slider.value()
            self.timer.start(self.timer_ms)
        elif self.started_status == 'PAUSE':
            self.timer.start(self.timer_ms)
            self.started_status = 'START'
            self.start_button.setText('Пауза')

    def stop_draw(self):
        self.timer.stop()
        self.started_status = 'STOP'
        self.start_button.setText('Старт')
        self.last_x = 0
        self.last_t = 0
        self.last_w = 0
        self.last_impulse = 0
        self.last_impulse_noise = 0
        self.last_cut_w = 0


def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = xolm()
    main_window.show()
    app.exec_()


if __name__ == '__main__':
    main()
