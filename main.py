# -*- coding: utf-8 -*-

import random
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
r = lambda: random.randint(0, 255)


class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None):
        self.fig, self.axarr = plt.subplots(4, sharex=True)
        self.labels_enable()
        self.fig.subplots_adjust(
            left=.1,
            bottom=.05,
            right=.96,
            top=.96,
            hspace=0.4,
        )
        self.grid_enable()
        super(MplCanvas, self).__init__(self.fig)

        for i in range(4):
            self.axarr[i].spines['top'].set_visible(False)
            self.axarr[i].spines['right'].set_visible(False)

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

        float_validator = QtGui.QDoubleValidator(0.0, 5.0, 10)
        int_validator = QtGui.QIntValidator(0, 10)
        float_validator.setLocale(QtCore.QLocale(QtCore.QLocale.English))

        for widget in (self.time_step_edit,
                       self.pile_length_edit,
                       self.pile_width_edit,
                       self.pile_depth_edit,
                       self.plunger_weight_edit,
                       self.coef_lower_pile_edit,
                       self.coef_soil_pile_edit,
                       self.resistance_surface_edit,
                       self.pile_m_weight_edit,
                       self.pile_thickness_edit,
                       self.noise_coef_edit):
            widget.textChanged.connect(self.param_change)
            widget.setValidator(float_validator)

        for widget in (self.plunger_pairs_edit,):
            widget.textChanged.connect(self.param_change)
            widget.setValidator(int_validator)

        self.speed_slider.valueChanged.connect(self.speed_boost)
        self.progress_status.pressed.connect(self.eg)

        self.sc = MplCanvas(self)
        self.draw_box_layout.addWidget(self.sc)
        self.draw_box_layout.addWidget(NavigationToolbar2(self.sc, self))
        self.axarr_0, = self.sc.axarr[0].plot(0, 0, linewidth=2, color='r')
        self.axarr_1, = self.sc.axarr[1].plot(0, 0, linewidth=2, color='g')
        self.axarr_2, = self.sc.axarr[2].plot(0, 0, linewidth=2, color='b')
        self.axarr_3, = self.sc.axarr[3].plot(0, 0, linewidth=2, color='m')

        self.started_status = 'STOP'

        self.timer = QtCore.QTimer()
        self.timer_ms = 75
        self.timer.timeout.connect(self.draw_tick)

        self.param_change(True)

        self.default_line_step = 0
        self.dynamic_line_step = 0
        self.current_step = 0

        self.egg = -42

    def eg(self):
        print(self.egg)
        self.egg += 1

    def speed_boost(self, s):
        self.dynamic_line_step = self.default_line_step * s

    def draw_tick(self):
        self.current_step += self.dynamic_line_step
        cut_t = self.t[:self.current_step]
        cut_x = self.x[:self.current_step]
        cut_w = self.w[:self.current_step]
        cut_impulse = self.impulse[:self.current_step]
        cut_impulse_noise = self.impulse_noise[:self.current_step]
        if len(self.t) >= self.current_step:
            self.axarr_0.set_data(cut_t, cut_x)
            self.axarr_1.set_data(cut_t, cut_w)
            self.axarr_2.set_data(cut_t, cut_impulse)
            self.axarr_3.set_data(cut_t, cut_impulse_noise)
            if not self.egg:
                self.axarr_0.set_color('#%02X%02X%02X' % (r(), r(), r()))
                self.axarr_1.set_color('#%02X%02X%02X' % (r(), r(), r()))
                self.axarr_2.set_color('#%02X%02X%02X' % (r(), r(), r()))
                self.axarr_3.set_color('#%02X%02X%02X' % (r(), r(), r()))
                self.axarr_0.set_linewidth(r())
                self.axarr_1.set_linewidth(r())
                self.axarr_2.set_linewidth(r())
                self.axarr_3.set_linewidth(r())
            for a in range(4):
                self.sc.axarr[a].relim()
                self.sc.axarr[a].autoscale_view()
            if self.tracking_toggle.isChecked():
                self.sc.axarr[0].set_xlim(cut_t[-1] - .1, cut_t[-1] + .01)
            else:
                self.sc.axarr[0].set_xlim(auto='auto')
            self.time_edit.setText(str(round(cut_t[-1], 2)))
            self.depth_edit.setText(str(round(cut_x[-1], 2)))
            self.speed_edit.setText(str(round(cut_w[-1], 2)))
            self.impulse_edit.setText(str(round(cut_impulse[-1], 2)))
            self.impulse_noise_edit.setText(str(round(cut_impulse_noise[-1], 2)))
            if cut_x[-1]:
                self.progress_bar.setValue(int(cut_x[-1] / self.l * 100))
            self.sc.fig.canvas.draw()
            self.sc.fig.canvas.flush_events()
        else:
            self.stop_draw()
            if self.progress_bar.value != 100:
                self.progress_status.setText('Свая погружена не полностью')

    def scan_param(self):
        self.g = 9.81
        # Количество пар дебалансов
        self.n = int(self.plunger_pairs_edit.text())
        # Шаг по времени
        self.dt = float(self.time_step_edit.text())
        # Длина сваи (м)
        self.l = float(self.pile_length_edit.text())
        # Ширина сваи (м)
        self.width_pipe = float(self.pile_width_edit.text())
        # Глубина сваи (м)
        self.depth_pipe = float(self.pile_depth_edit.text())
        # Толщина стенки сваи (м)
        self.pile_thickness = float(self.pile_thickness_edit.text())
        # Периметр основания сваи (м)
        self.pile_perimeter = self.width_pipe * 2 + self.depth_pipe * 2
        # Площадь основания сваи (м^2)
        self.pile_area = self.width_pipe * self.depth_pipe - (self.width_pipe - self.pile_thickness) * (self.depth_pipe - self.pile_thickness)
        # Вес погружателя (кг)
        self.plunger_weight = float(self.plunger_weight_edit.text())
        # Вес 1 метра сваи (кг)
        self.pile_weight_m = float(self.pile_m_weight_edit.text())
        # Вес всей сваи (кг)
        self.pile_weight = self.l * self.pile_weight_m * 4
        # Вес машинки + сваи (кг)
        self.M = self.plunger_weight + self.pile_weight
        # Коэффициент условий работы грунта под нижним концом сваи
        self.gamma_cr = float(self.coef_lower_pile_edit.text())
        # Коэффициент условий работы грунта на боковой поверхности
        self.gamma_cf = float(self.coef_soil_pile_edit.text())
        # Расчётное сопротивлене по боковой поверхности (кПа)
        self.fi = float(self.resistance_surface_edit.text())
        # Коэффициент шума
        self.noise_coef = float(self.noise_coef_edit.text())

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
            self.progress_status.setText('Погружение приостановлено')
        elif self.started_status == 'STOP':
            self.started_status = 'START'
            self.start_button.setText('Пауза')
            self.progress_status.setText('Расчет данных...')
            self.axarr_0.set_data(0, 0)
            self.axarr_1.set_data(0, 0)
            self.axarr_2.set_data(0, 0)
            self.axarr_3.set_data(0, 0)
            self.progress_bar.setValue(0)
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
                self.fi,
                self.noise_coef
            )
            if len(self.x) < 3500:
                self.default_line_step = 1
            else:
                self.default_line_step = len(self.x) // 3500
            self.progress_status.setText('Погружение...')
            self.dynamic_line_step = self.default_line_step * self.speed_slider.value()
            self.timer.start(self.timer_ms)
        elif self.started_status == 'PAUSE':
            self.timer.start(self.timer_ms)
            self.started_status = 'START'
            self.start_button.setText('Пауза')
            self.progress_status.setText('Погружение...')

    def stop_draw(self):
        self.timer.stop()
        self.started_status = 'STOP'
        self.start_button.setText('Старт')
        self.progress_status.setText('Погружение не начато')
        self.current_step = 0


def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = xolm()
    main_window.show()
    app.exec_()


if __name__ == '__main__':
    main()
