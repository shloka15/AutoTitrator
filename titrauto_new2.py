import sys
import time
import serial
import os
import re
import numpy as np
import subprocess
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtWidgets import *

serial_port = 'COM4'  # Replace with actual COM port
baud_rate = 9600

# Global lists to store data points
x_data = []
y_data = []
markers = []


# The class that reads serial data and creates logged data files
class SerialDataReader:
    def __init__(self, serial_port, data_file_path, description):
        self.ser = serial_port
        self.x_data = []
        self.y_data = []
        self.data_file_path = data_file_path
        self.description = description
        self.start_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.initialize_data_file()

    def initialize_data_file(self):
        default_file_path = "D:\\Shloka\\GUI\\default.txt"

        with open(self.data_file_path, 'w') as data_file:    
            # Read 4 lines from default.txt and write to the new file
            with open(default_file_path, 'r') as default_file:
                for _ in range(4):
                    default_line = default_file.readline().strip()
                    data_file.write(default_line + '\n')

                default_line = default_file.readline().strip()
                default_line = default_file.readline().strip()
                our_line = default_line.split(" ")
                if our_line[0] == 'Temperature':
                    data_file.write(default_line + '\n')

            # Write the description
            data_file.write(f"\nDescription: {self.description}\n")
            data_file.write(f"Start Time: {self.start_time}\n")
            data_file.write('\n')
            data_file.flush()

    def write_start_time(self):
        with open(self.data_file_path, 'a') as data_file:
            data_file.write(f"Start Time: {self.start_time}\n")
            data_file.flush()

    def write_stop_time(self):
        stop_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        with open(self.data_file_path, 'r') as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            if line.startswith("Start Time:"):
                lines.insert(i + 1, f"Stop Time: {stop_time}\n")
                break

        with open(self.data_file_path, 'w') as file:
            file.writelines(lines)

    def read_serial_data(self):
        if self.ser.in_waiting > 0:
            try:
                sam, tit, ini, com = map(float,self.param_data())
                line = self.ser.readline().decode('utf-8').strip()
                parts = line.split(" ")
                
                if len(parts) == 5:
                    Time, cond, temp, marker, xvol = map(float, parts)
                    if marker==0.00:
                        pass

                    elif marker == 1.00:
                        x_data.append(xvol)

                        conduc = cond*(((sam*1000)+ini+tit)/(sam*1000))  
                        if com == 1.00:
                            conduct = conduc/(1+0.02*(temp-25.00))
                            conduc = conduct
                        y_data.append(conduc)  
            
                    with open(self.data_file_path, 'a') as data_file:
                        data_file.write(line + '\n')
                        data_file.flush()
                else:
                    print(f"Unexpected number of values: {line}")
            except:
                print(f"Error parsing line.")
                with open(self.data_file_path, 'a') as data_file:
                    data_file.write("0.00 0.00 0.00 0.00 0.00" + '\n')
                    data_file.flush()
                pass

    def param_data(self):
        default_file_path = "D:\\Shloka\\GUI\\default.txt"
        with open(default_file_path, 'r') as default_file:
            for _ in range(6):
                default_line = default_file.readline().strip().split()
                if default_line[0] == 'Sample':
                    sample = float(default_line[2])
                elif default_line[0] == 'Titrant':
                    titrant = float(default_line[2])
                elif default_line[0] == 'Initial':
                    initial = float(default_line[2])
                elif default_line[0] == 'Temperature':
                    compen = default_line[2]
                    if compen == 'Yes':
                        comp = 1.00
                    else:
                        comp = 0.00

        return sample,titrant,initial,comp


# The class of the graph
class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None):
        fig, self.ax = plt.subplots()
        super().__init__(fig)
        self.setParent(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        self.plot()

    def plot(self):
        self.ax.clear()
        self.ax.plot(x_data, y_data, linestyle='-', marker='o')
        self.ax.set_title('Titration')
        self.ax.set_xlabel('Titrant Volume (uL)')
        self.ax.set_ylabel('Conductivity (uS/cm)')
        self.draw()

    def plot_review(self, y_values, x_values):
        self.ax.clear()
        self.ax.plot(x_values, y_values, linestyle='-', marker='o', color='blue', label='Marker')
        self.ax.set_title('Review Titration')
        self.ax.set_xlabel('Titrant Volume (uL)')
        self.ax.set_ylabel('Conductivity (uS/cm)')
        self.ax.legend()
        self.x_values = x_values
        self.y_values = y_values
        self.cursor_index = 0
        self.cursor, = self.ax.plot([self.x_values[self.cursor_index]], [self.y_values[self.cursor_index]], marker='+', color='black', markersize=10)
        self.selected_points = []
        self.num_fits = 0  
        self.draw()

    def clear_plot(self):
        self.ax.clear()
        self.ax.set_title('')
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        self.draw()

    def plot_overlay(self, y_values, x_values, color):
        self.ax.plot(x_values, y_values, linestyle='-', marker='o', color=color, label=f'Overlay {len(self.ax.lines)}')
        self.ax.legend()
        self.draw()

    # For background check
    def update_val(self, x, y):
        x_data.append(x)
        y_data.append(y)
        self.plot()
        
    # For endpoint detection
    def move_cursor(self,direction):
        if direction == 'left' and self.cursor_index > 0:
            self.cursor_index -= 1
            #print(f'Moved left to index {self.cursor_index}')
        elif direction == 'right' and self.cursor_index < len(self.x_values) - 1:
            self.cursor_index += 1
            #print(f'Moved right to index {self.cursor_index}')
        self.update_cursor()

    def update_cursor(self):
        self.cursor.set_data([self.x_values[self.cursor_index]], [self.y_values[self.cursor_index]])
        #print(f'Updated cursor to position: {self.x_values[self.cursor_index]}, {self.y_values[self.cursor_index]}')
        self.draw()

    def select_point(self):
        if len(self.selected_points) < 4:
            x, y = self.x_values[self.cursor_index], self.y_values[self.cursor_index]
            self.selected_points.append((self.cursor_index, (x, y)))
            self.ax.plot(x, y, marker='o', color='green')
            #print(f'Selected point: {x}, {y}')
            self.draw()
            if len(self.selected_points) == 4:
                self.calculate_least_squares()

    def calculate_least_squares(self):
        # Sort points by index
        self.selected_points.sort()
        idx_pairs = [(self.selected_points[i], self.selected_points[i + 1]) for i in range(0, len(self.selected_points), 2)]

        lines = []

        for idx1, idx2 in idx_pairs:
            start_idx, point1 = idx1
            end_idx, point2 = idx2

            # Extract all points between the selected indices
            x = self.x_values[start_idx:end_idx + 1]
            y = self.y_values[start_idx:end_idx + 1]

            # Least squares fit
            A = np.vstack([x, np.ones(len(x))]).T
            m, c = np.linalg.lstsq(A, y, rcond=None)[0]

            lines.append((m, c, start_idx, end_idx))

        # Calculate intersection point
        if len(lines) == 2:
            m1, c1, start_idx1, end_idx1 = lines[0]
            m2, c2, start_idx2, end_idx2 = lines[1]
            if m1 != m2:
                x_intersect = (c2 - c1) / (m1 - m2)
                y_intersect = m1 * x_intersect + c1
                print(f'Intersection point: ({x_intersect}, {y_intersect})')

                for m, c, start_idx, end_idx in lines:
                    x_min = self.x_values[start_idx]
                    x_max = self.x_values[end_idx]

                    x_fit_min = max(x_min, min(x_min, x_intersect))
                    x_fit_max = min(x_max, max(x_max, x_intersect))

                    x_fit = np.array([x_fit_min, x_intersect, x_fit_max])
                    y_fit = m * x_fit + c
                    self.ax.plot(x_fit, y_fit, 'r-')
                    print(f'Least squares fit line: y = {m}x + {c}')

                # Vertical line at intersection point
                y_min = min(self.y_values)
                y_max = max(self.y_values)
                self.ax.axvline(x=x_intersect, color='black', linestyle='--')
                #print(f'Drew vertical line at x = {x_intersect}')

                self.selected_points = []
                self.num_fits += 1
                if self.num_fits == 2:
                    pass
                    #print("Finished drawing two sets of least squares fit lines.")

        self.draw()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            self.select_point()
        elif event.key() == Qt.Key_Left:
            self.move_cursor('left')
        elif event.key() == Qt.Key_Right:
            self.move_cursor('right')


# The Input Dialog after you click Analysis
class InputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Required")
        self.setFixedSize(600, 360)  # Increase the size of the dialog

        self.main_layout = QVBoxLayout(self)  # Use a vertical layout for the main layout

        self.inputs = []

        self.default_values = self.load_default_values("D:\\Shloka\\GUI\\default.txt")

        # Main layout for group boxes side by side
        self.group_boxes_layout = QHBoxLayout()    
       
        # GroupBox for first set of inputs
        self.groupBox = QGroupBox(self)
        groupBox_layout = QVBoxLayout(self.groupBox)
        self.groupBox.setFixedSize(280, 170)  # Increase size of the group box


        # GroupBox for second set of inputs
        self.groupBox_2 = QGroupBox(self)
        groupBox_2_layout = QVBoxLayout(self.groupBox_2)
        self.groupBox_2.setFixedSize(280, 170)  # Increase size of the group box  
       
        self.create_inputs(groupBox_layout, groupBox_2_layout)  
       
        self.temperature_compensation = QCheckBox("Temperature Compensation", self)
        #self.temperature_compensation.setChecked(False)  # Set to unchecked by default
        self.temperature_compensation.toggled.connect(self.update_temperature_compensation)
       
        self.label_8 = QLabel("Select PATH:", self)
        self.STF_lab=QLabel("Save to .txt File:")
        self.STF_inp=QLineEdit(placeholderText="Enter File Path")
        self.browse_button = QPushButton('Browse')
        self.browse_button.clicked.connect(self.browse_file)
       
        self.DLC_lay = QHBoxLayout()
        self.DLC_lay.addWidget(self.label_8)
        self.DLC_lay.addWidget(self.STF_inp)
        self.DLC_lay.addWidget(self.browse_button)
       
        self.controls_lay = QVBoxLayout()
        self.controls_lay.addLayout(self.DLC_lay)
       
        self.label_7 = QLabel("Description:", self)

        self.textEdit = QTextEdit(self)
        self.textEdit.setFixedSize(560, 48)  # Decrease size of the description box to 60% of its original size

        # Creating a horizontal layout for the buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK", self)
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.update_default_values)
        self.ok_button.clicked.connect(self.modifySketch)
        self.ok_button.clicked.connect(self.enable_start)
       
        self.start_button = QPushButton("Start", self)
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.uploadSketchToArduino)
        self.start_button.clicked.connect(self.accept)  #CHECK
       
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.start_button)

        self.group_boxes_layout.addWidget(self.groupBox)
        self.group_boxes_layout.addWidget(self.groupBox_2)
        self.main_layout.addLayout(self.group_boxes_layout)
        self.main_layout.addWidget(self.temperature_compensation)
        self.main_layout.addSpacerItem(QSpacerItem(2, 2, QSizePolicy.Minimum, QSizePolicy.Expanding))  # Add vertical space
        self.main_layout.addLayout(self.controls_lay)
        self.main_layout.addWidget(self.label_7)
        self.main_layout.addWidget(self.textEdit)
        self.main_layout.addLayout(self.button_layout)

        self.groupBox.setLayout(groupBox_layout)
        self.groupBox_2.setLayout(groupBox_2_layout)
        self.setLayout(self.main_layout)
       
        self.check_fields()

    def modifySketch(self):
        try:
            # Read values from the .txt file
            file_path = 'D:\\Shloka\\GUI\\default.txt'
            with open(file_path, 'r') as file:
                values = file.readlines()

            # Extract values
            tit = float(values[1].strip().split()[2])
            mix = float(values[2].strip().split()[2])
            ini = float(values[3].strip().split()[2])
            endi = float(values[4].strip().split()[2])

            # Path to the .ino file
            sketch_path = "D:\\Shloka\\arduino_UNO_sample_codes\\semifinal_arduino\\semifinal_arduino.ino"

            # Read the existing .ino file
            with open(sketch_path, 'r') as file:
                sketch_content = file.read()

            # Replace values in the sketch
            sketch_content = re.sub(r'const float tit\s*=\s*[-+]?[0-9]*\.?[0-9]+;', f'const float tit = {tit};', sketch_content)
            sketch_content = re.sub(r'const float mix\s*=\s*[-+]?[0-9]*\.?[0-9]+;', f'const float mix = {mix};', sketch_content)
            sketch_content = re.sub(r'const float ini\s*=\s*[-+]?[0-9]*\.?[0-9]+;', f'const float ini = {ini};', sketch_content)
            sketch_content = re.sub(r'const float endi\s*=\s*[-+]?[0-9]*\.?[0-9]+;', f'const float endi = {endi};', sketch_content)

            # Write the modified content back to the .ino file
            with open(sketch_path, 'w') as file:
                file.write(sketch_content)

            print("Sketch modified successfully.")

        except Exception as e:
            print(f"Error modifying sketch: {e}")

        time.sleep(2)

    def compile_sketch(self, sketch_path, arduino_path):
        # Path to the Arduino IDE
        arduino_ide_path = os.path.join(arduino_path, "arduino_debug.exe")

        # Compile the sketch
        compile_command = [
            arduino_ide_path,
            "--verify",
            "--pref", "build.path=build",
            sketch_path
        ]

        result = subprocess.run(compile_command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Compilation Error: {result.stderr}")
            return None
        else:
            print(f"Compilation Success: {result.stdout}")
            return os.path.join("build", os.path.basename(sketch_path).replace(".ino", ".ino.hex"))


    def upload_hex_to_arduino(self, hex_file_path, port, board_type):
        # Path to avrdude
        avrdude_path = "C:\\Program Files (x86)\\Arduino\\hardware\\tools\\avr\\bin\\avrdude.exe"

        # Path to avrdude configuration file
        avrdude_conf_path = "C:\\Program Files (x86)\\Arduino\\hardware\\tools\\avr\\etc\\avrdude.conf"

        mcu = "atmega328p"
        programmer = "arduino"

        # avrdude command
        avrdude_command = [
            avrdude_path,
            "-C", avrdude_conf_path,
            "-v",
            "-p", mcu,
            "-c", programmer,
            "-P", port,
            "-b", "115200",
            "-D",
            "-U", f"flash:w:{hex_file_path}:i"
        ]

        # Run the command
        result = subprocess.run(avrdude_command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
        else:
            print(f"Success: {result.stdout}")

    
    def uploadSketchToArduino(self):
        arduino_path = "C:\\Program Files (x86)\\Arduino"
        sketch_path = "D:\\Shloka\\arduino_UNO_sample_codes\\semifinal_arduino\\semifinal_arduino.ino"
        port = serial_port
        hex_file_path = self.compile_sketch(sketch_path, arduino_path)
        if hex_file_path:
            board_type = "uno"
            self.upload_hex_to_arduino(hex_file_path, port, board_type)

    def upload_background_sketch(self):
        arduino_path = "C:\\Program Files (x86)\\Arduino"
        sketch_path = "D:\\Shloka\\arduino_UNO_sample_codes\\EC_code\\EC_code.ino"
        port = serial_port
        hex_file_path = self.compile_sketch(sketch_path, arduino_path)
        if hex_file_path:
            board_type = "uno"
            self.upload_hex_to_arduino(hex_file_path, port, board_type)
  
    def browse_file(self):
        file_dialog = QFileDialog()
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)  
        file_dialog.setDefaultSuffix("txt")  
        file_dialog.setNameFilter("Text files (*.txt)")
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                self.STF_inp.setText(selected_files[0])

    def get_data_file_path(self):
        return self.STF_inp.text()

    def get_description(self):
        return self.textEdit.toPlainText().strip()
       
    def create_inputs(self, groupBox_layout, groupBox_2_layout):
        labels = [
            "Type of Titration", "Sample Volume (mL)", "Titrant Volume (uL)",
            "Mixing Time (seconds)", "Initial Volume of Titrant (uL)", "End Volume (uL)"
        ]

        for i, label_text in enumerate(labels):
            layout = QHBoxLayout()
            label = QLabel(label_text, self)
            layout.addWidget(label)

            if label_text == "Type of Titration":
                dropdown = QComboBox(self)
                dropdown.addItems(["Conductivity (k)", "pH", "ORP"])
                layout.addWidget(dropdown)
                self.inputs.append(dropdown)
                dropdown.currentIndexChanged.connect(self.check_fields)
            else:
                line_edit = QLineEdit(self)
                line_edit.setMaximumWidth(100)  

                label_text = label_text.split()
                label_text = label_text[0:2]
               
                label_text = ' '.join(label_text)
                                               
                # Set default value if available
                if label_text in self.default_values:
                    line_edit.setText(self.default_values[label_text])

                layout.addWidget(line_edit)
                self.inputs.append(line_edit)
                line_edit.textChanged.connect(self.check_fields)  

            if i < 3:
                groupBox_layout.addLayout(layout)
            else:
                groupBox_2_layout.addLayout(layout)
               
    def update_temperature_compensation(self):
        self.default_values["Temperature Compensation"] = "No"
        if self.temperature_compensation.isChecked():
            self.default_values["Temperature Compensation"] = "Yes"
        with open("D:\\Shloka\\GUI\\default.txt", 'w') as file:
            for key, value in self.default_values.items():
                file.write(f"{key}: {value}\n")

    def check_fields(self):
        all_filled = True
        for input_field in self.inputs:
            if isinstance(input_field, QLineEdit):
                if not input_field.text():
                    all_filled = False
                    break
            elif isinstance(input_field, QComboBox):
                if input_field.currentIndex() == -1:
                    all_filled = False
                    break
        self.ok_button.setEnabled(all_filled)

    def enable_start(self):
        self.start_button.setEnabled(True)

    def load_default_values(self, filename):
        default_values = {}
        try:
            with open(filename, 'r') as file:
                for line in file:
                    key, vol, value = line.split()
                    default_values[key + " Volume"] = value
                    if key == "Mixing":
                        default_values["Mixing Time"] = value
                    elif key == "Initial":
                        default_values["Initial Volume of Titrant"] = value
                    elif key == "Temperature":
                        default_values["Temperature Compensation:"] = value
        except FileNotFoundError:
            print(f"File {filename} not found.")
        return default_values

    def update_default_values(self):
        keys = ["Sample Volume", "Titrant Volume", "Mixing Time", "Initial Volume of Titrant", "End Volume", "Temperature Compensation"]
        with open("D:\\Shloka\\GUI\\default.txt", 'w') as file:
            for i, key in enumerate(keys):
                if key == "Type of Titration":
                    value = self.inputs[i].currentText()
                elif key == "Temperature Compensation":
                    value = self.default_values["Temperature Compensation:"]
                else:
                    value = self.inputs[i+1].text()
                value_label = key.split()[0]  
                if value_label == 'Sample':
                    file.write(f"{value_label} Volume(mL): {value}\n")
                elif value_label == 'Titrant':
                    file.write(f"{value_label} Volume(uL): {value}\n")
                elif value_label == 'Mixing':
                    file.write(f"{value_label} Time(s): {value}\n")
                elif value_label == 'Initial':
                    file.write(f"{value_label} Volume(uL): {value}\n")
                elif value_label == 'End':
                    file.write(f"{value_label} Volume(uL): {value}\n")
                elif value_label == 'Temperature':
                    file.write(f"{value_label} Compensation: {value}\n")

        time.sleep(1)

           
# The Main Window
class ATWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Titrator")
        self.serial_data_reader = None

        # Defining Dialog Box for Startup
        msgBox = QMessageBox()
        msgBox.setIconPixmap(QPixmap("ClientIcon.ico"))
        msgBox.setWindowTitle("AUTO TITRATOR GUI")
        msgBox.setWindowIcon(QIcon("ClientIcon.ico"))
        msgBox.setText("TITRAUTO")
        msgBox.setInformativeText("\nVersion 1.0.0\nDeveloped by BITS-Pilani")
        msgBox.exec()

        # Initiating home page
        self.HomePage()

        # Adding it to a stacked layout and raising it for display
        self.stacked_layout = QStackedLayout()
        self.stacked_layout.addWidget(self.HomePage_widget)
        self.stacked_layout.setCurrentIndex(0)

        self.setWindowIcon(QIcon("ClientIcon.ico"))

        # Setting stacked layout as a central widget for our main window
        self.Central_widget = QWidget()
        self.Central_widget.setLayout(self.stacked_layout)
        self.setCentralWidget(self.Central_widget)

        self.serial_timer = QTimer()
        self.serial_timer.timeout.connect(self.read_serial_data)

        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plot)

        self.ser = None  # Serial port is not initialized here
        self.data_reader = None
        self.export_file = None
        self.input_dial = InputDialog(self)


    def HomePage(self):
        # Setting up layout of the page:
        # Defining buttons, text Box and a secondary layout
        self.BackgroundBut = QPushButton("Background Check")
        self.CalibrateBut = QPushButton("Calibrate")
        self.AnalysisBut = QPushButton("Analysis")

        self.OfflineLabel = QLabel("Offline Mode")
        self.RevBut = QPushButton("Review")
        self.OvBut = QPushButton("Overlay")
        self.EndBut = QPushButton("Endpoints")

        self.ExportBut = QPushButton("Export")
        self.ExitBut = QPushButton("Exit")

        self.ex1 = QVBoxLayout()
        self.ex1grp = QGroupBox()

        self.ex1.addWidget(self.AnalysisBut)
        self.ex1 = QVBoxLayout()
        self.ex1.addWidget(self.OfflineLabel, alignment=Qt.AlignCenter)
        for i in [self.BackgroundBut, self.CalibrateBut, self.AnalysisBut]:
            self.ex1.addWidget(i)
        self.ex1grp.setLayout(self.ex1)

        self.ex2grp = QGroupBox()
        self.ex2 = QVBoxLayout()
        self.ex2.addWidget(self.OfflineLabel, alignment=Qt.AlignCenter)
        for i in [self.RevBut, self.OvBut, self.EndBut]:
            self.ex2.addWidget(i)
        self.ex2grp.setLayout(self.ex2)

        self.ex3grp = QGroupBox()
        self.ex3 = QVBoxLayout()

        self.date_time_label = QLabel(self)
        self.ex3.addWidget(self.date_time_label, alignment=Qt.AlignRight)

        self.ex3.addWidget(self.ExportBut)
        self.ex3.addWidget(self.ExitBut)

        self.ex3grp.setLayout(self.ex3)

        self.tempWid = QGroupBox()  # A master layout for BOX 1 and 2
        self.tempLay1 = QVBoxLayout()
        self.tempLay1.addWidget(self.ex1grp)
        self.tempLay1.addWidget(self.ex2grp)
        self.tempLay1.addWidget(self.ex3grp)
        self.tempWid.setLayout(self.tempLay1)

        # Defining canvas and navigation bar
        self.plot_canvas = PlotCanvas(self)
        self.Tb = NavigationToolbar(self.plot_canvas, self)

        self.tempWid2 = QGroupBox()  # A secondary layout for canvas and navigation Bar
        self.tempLay2 = QVBoxLayout()
        self.tempLay2.addWidget(self.plot_canvas)
        self.tempLay2.addWidget(self.Tb)
        self.tempWid2.setLayout(self.tempLay2)

        # A master layout for all secondary layouts
        self.Mode_layout = QGridLayout()
        self.Mode_layout.addWidget(self.tempWid, 1, 1)
        self.Mode_layout.addWidget(self.tempWid2, 1, 3)

        self.update_date_time()  # Update date and time initially
        self.start_timer()  # Start timer to update date and time

        self.HomePage_widget = QWidget()
        self.HomePage_widget.setLayout(self.Mode_layout)
        self.HomePage_widget.setGeometry(100, 100, 800, 600)
        self.HomePage_widget.setWindowTitle("Auto Titrator")

        # Connect the buttons to their actions
        self.ExitBut.clicked.connect(self.close)
        self.ExportBut.clicked.connect(self.export_data)
        self.AnalysisBut.clicked.connect(self.toggle_analysis)
        self.CalibrateBut.clicked.connect(self.toggle_calibrate)
        self.BackgroundBut.clicked.connect(self.toggle_background)
        self.RevBut.clicked.connect(self.toggle_review)
        self.OvBut.setEnabled(False)
        self.OvBut.clicked.connect(self.toggle_overlay)
        self.EndBut.setEnabled(False)
        self.EndBut.clicked.connect(self.toggle_endpoints)

    
    def export_data(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        if file_dialog.exec_():
            self.file_path = file_dialog.selectedFiles()[0]
        exported_path = self.file_path[:-4] + "_exported.txt"
        self.export_file = exported_path
        
        if self.export_file:
            self.save_exported_data(self.file_path, self.export_file)

    def save_exported_data(self, input_file, output_file):
        with open(input_file, 'r') as file:
            lines = file.readlines()

        with open(output_file, 'w') as file:
            for line in lines:
                parts = line.split()
                if len(parts) == 5:
                    _, cond, temp, marker, xvol = map(float, parts)
                    if marker == 1.00:
                        file.write(f"{cond} {temp} {xvol}\n")

    def update_date_time(self):
        current_datetime = QDateTime.currentDateTime()
        date_str = current_datetime.toString("d MMMM yyyy")
        time_str = current_datetime.toString("hh:mm")
        self.date_time_label.setText(f"{date_str}, {time_str}")

    def start_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_date_time)
        self.timer.start(1000)  # Update every second

    def toggle_background(self):
        if self.serial_timer.isActive():
            self.serial_timer.stop()
            self.plot_timer.stop()
            if self.data_reader and self.data_reader.is_alive():
                self.data_reader.terminate()
            self.ser.close()
            self.ser = None
            self.data_reader = None
            self.BackgroundBut.setText("Background Check")
            self.AnalysisBut.setEnabled(True)
            self.CalibrateBut.setEnabled(True)
            self.RevBut.setEnabled(True)
            self.ExportBut.setEnabled(True)
            self.ExitBut.setEnabled(True)
        else:
            self.BackgroundBut.setText("Stop Check")
            self.AnalysisBut.setEnabled(False)
            self.CalibrateBut.setEnabled(False)
            self.RevBut.setEnabled(False)
            self.OvBut.setEnabled(False)
            self.EndBut.setEnabled(False)
            self.ExportBut.setEnabled(False)
            self.ExitBut.setEnabled(False)
            self.background_check()

    def background_check(self):
        self.input_dial.upload_background_sketch()  
        self.ser = serial.Serial(serial_port, baud_rate, timeout=1)
        self.serial_timer.start(1000)  # Check for serial data every second
        self.plot_timer.start(1000)    # Update the plot every second
        self.read_bg_data()

    def read_bg_data(self):
        if self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                if line:
                    x_val, y_val = map(float,line.split(" "))
                    self.plot_canvas.update_val(x_val, y_val)
                    print(f"Read serial data: {value}")  
            except Exception as e:
                print(f"Error reading serial data: {e}")

    def toggle_analysis(self):
        if self.serial_timer.isActive():
            self.serial_timer.stop()
            self.plot_timer.stop()
            self.ser.close()
            self.ser = None
            self.data_reader = None
            self.serial_data_reader.write_stop_time()
            self.serial_data_reader = None
            self.AnalysisBut.setText("Analysis")
            self.BackgroundBut.setEnabled(True)
            self.CalibrateBut.setEnabled(True)
            self.RevBut.setEnabled(True)
            self.ExportBut.setEnabled(True)
            self.ExitBut.setEnabled(True)
        else:
            dialog = InputDialog(self)
            if dialog.exec() == QDialog.Accepted:
                self.AnalysisBut.setText("Stop Analysis")
                self.BackgroundBut.setEnabled(False)
                self.CalibrateBut.setEnabled(False)
                self.RevBut.setEnabled(False)
                self.OvBut.setEnabled(False)
                self.EndBut.setEnabled(False)
                self.ExportBut.setEnabled(False)
                self.ExitBut.setEnabled(False)
                self.data_file_path = dialog.get_data_file_path()
                self.description = dialog.get_description()
                self.serial_data_reader = SerialDataReader(self.ser, self.data_file_path, self.description)
                self.start_analysis(self.data_file_path,self.description)

    def start_analysis(self,data_file_path,desc):
        self.ser = serial.Serial(serial_port, baud_rate, timeout=1)
        self.data_reader = SerialDataReader(self.ser, data_file_path, desc)
        self.serial_timer.start(1000)  # Check for serial data every second
        self.plot_timer.start(1000)    # Update the plot every second

    def read_serial_data(self):
        if self.data_reader:
            self.data_reader.read_serial_data()

    def update_plot(self):
        self.plot_canvas.plot()

    def toggle_review(self):
        if self.RevBut.text() == "Quit Review":
            self.plot_canvas.clear_plot()
            self.RevBut.setText("Review")
            self.BackgroundBut.setEnabled(True)
            self.CalibrateBut.setEnabled(True)
            self.AnalysisBut.setEnabled(True)
            self.OvBut.setEnabled(False)
            self.EndBut.setEnabled(False)
            self.ExportBut.setEnabled(True)
            self.ExitBut.setEnabled(True)
        else:
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Analysis File", "", "Text Files (*.txt);;All Files (*)", options=options)
            if file_path:
                y_values, x_values = self.read_data_from_file(file_path)
                self.RevBut.setText("Quit Review")
                self.BackgroundBut.setEnabled(False)
                self.CalibrateBut.setEnabled(False)
                self.AnalysisBut.setEnabled(False)
                self.OvBut.setEnabled(True)
                self.EndBut.setEnabled(True)
                self.ExportBut.setEnabled(False)
                self.ExitBut.setEnabled(False)
                self.plot_canvas.plot_review(y_values, x_values)
                self.plot_canvas.setFocus()  # Set focus to the plot canvas for key events

    # Function to read and parse the data from the file
    def read_data_from_file(self, filename):
        y_values = []
        x_values = []

        with open(filename, 'r') as file:
            lines = file.readlines()[10:]  # Skip the first 10 lines

            for line in lines:
                parts = line.split()
                if len(parts) > 4 and parts[3] == '1.00':
                    x_values.append(float(parts[4]))
                    y_values.append(float(parts[1]))

        return y_values, x_values

    def toggle_overlay(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Analysis File", "", "Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            y_values, x_values = self.read_data_from_file(file_path)
            existing_plots = len(self.plot_canvas.ax.lines)
            
            if existing_plots == 1:
                color = 'red'
            elif existing_plots == 2:
                color = 'green'
            elif existing_plots == 3:
                color = 'black'
            elif existing_plots == 4:
                color = 'yellow'
            else:
                color = 'white'
            
            self.plot_canvas.plot_overlay(y_values, x_values, color)

            if existing_plots >= 4:
                self.OvBut.setEnabled(False)

    def toggle_endpoints(self):
        self.plot_canvas.selected_points = []
        self.plot_canvas.cursor_index = 0
        self.plot_canvas.cursor.set_data([self.plot_canvas.x_values[self.plot_canvas.cursor_index]], [self.plot_canvas.y_values[self.plot_canvas.cursor_index]])
        self.plot_canvas.draw()
        self.plot_canvas.setFocus()  # Set focus to the plot canvas for key events


    def toggle_calibrate(self):
        self.AnalysisBut.setEnabled(False)
        self.RevBut.setEnabled(False)
        self.OvBut.setEnabled(False)
        self.EndBut.setEnabled(False)
        self.ExportBut.setEnabled(False)
        self.ExitBut.setEnabled(False)

        # Create a message box for the instructions
        msg = QMessageBox()
        msg.setWindowTitle("Calibration Instructions")
        msg.setText("""Follow the instructions for calibration:\n
        1. Make sure your setup is completely dry. Get continuous readings.\n
        2. Set Cal, K according to your probe. (Eg. : 0.1, 1.0, 10)\n
        3. Run Cal, dry. Wait till you get 0.00 constantly.\n
        4. Follow the procedure for a 2-point calibration as given in the datasheet\n
           for the EZO-EC conductivity IC.\n
           
           You are ready to start the analysis!""")
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)

        # Show the message box and wait for user to press OK
        retval = msg.exec_()

        if retval == QMessageBox.Ok:
            # Enable buttons if needed after closing the instructions
            self.AnalysisBut.setEnabled(True)
            self.RevBut.setEnabled(True)
            self.ExportBut.setEnabled(True)
            self.ExitBut.setEnabled(True)
        

# Final Run
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = ATWindow()
    main_window.show()
    sys.exit(app.exec_())
# End.