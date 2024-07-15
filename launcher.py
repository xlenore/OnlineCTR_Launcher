import configparser
import os
import re
import subprocess
import sys
import threading
import warnings
import psutil
import requests
import shutil
import zipfile
#import debugpy
import time


from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


warnings.filterwarnings('ignore')

LAUNCHER_VERSION = "1.3b2"

URL_CLIENT = "https://online-ctr.com/wp-content/uploads/onlinectr_patches/client.zip"
URL_XDELTA_30 = "https://online-ctr.com/wp-content/uploads/onlinectr_patches/ctr-u_Online30.xdelta"
URL_XDELTA_60 = "https://online-ctr.com/wp-content/uploads/onlinectr_patches/ctr-u_Online60.xdelta"
URL_CURRENT_VERSION = "https://online-ctr.com/wp-content/uploads/onlinectr_patches/build.txt"


if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(os.path.realpath(sys.executable))
elif __file__:
    application_path = os.path.dirname(__file__)


#Kill launcher.exe if already running
current_pid = os.getpid()
for proc in psutil.process_iter(['pid', 'name']):
    if proc.info['name'] in ['launcher.exe', 'client.exe', 'duckstation-qt-x64-ReleaseLTCG.exe'] and proc.info['pid'] != current_pid:
        proc.kill()


class LauncherSettings:
    def __init__(self):
        self.config = configparser.ConfigParser(inline_comment_prefixes=";")
        try:
            self.config.read("settings.ini")
            self.name = self.config["SETTINGS"]["name"].strip('"')
            self.frame_rate = self.config["SETTINGS"]["frame_rate"].strip('"')
            self.duckstation = self.config["PATHS"]["duckstation"].strip('"')
            self.game_rom = self.config["PATHS"]["game_rom"].strip('"')
            self.fullscreen = self.config["SETTINGS"]["fullscreen"].strip('"')
            self.fast_boot = self.config["SETTINGS"]["fast_boot"].strip('"')
        except Exception as e:
            self.name = "YourName"
            self.frame_rate = "0"
            self.duckstation = r"C:\Users\[yourUserName]\[remaining path to duckstation folder]\duckstation-qt-x64-ReleaseLTCG.exe"
            self.game_rom = r"C:\Users\[yourUserName]\[remaining path to game rom]\CTR.bin"
            self.fullscreen = "0"
            self.fast_boot = "0"
            self.save_settings()
            
    def save_settings(self):
        self.config["SETTINGS"] = {
            "name": f'"{self.name}" ; Your name in the game',
            "frame_rate": f'{self.frame_rate} ; 0 = 30fps, 1 = 60fps',
            "fullscreen": f'{self.fullscreen} ; 0 = disabled, 1 = enabled',
            "fast_boot": f'{self.fast_boot} ; 0 = disabled, 1 = enabled'
        }
        self.config["PATHS"] = {
            "duckstation": f'"{self.duckstation}"',
            "game_rom": f'"{self.game_rom}"'
        }
        with open("settings.ini", "w") as file:
            self.config.write(file)
    
    def get_player_name(self):
        return self.name

    def get_frame_rate(self):
        return self.frame_rate

    def get_fast_boot(self):
        return self.fast_boot

    def get_fullscreen(self):
        return self.fullscreen

    def get_duckstation_path(self):
        return self.duckstation

    def get_game_rom_path(self):
        return self.game_rom


class GameLauncher:
    def __init__(self, root_folder, gui, settings):
        self.root_folder = root_folder
        self.xdelta_path = os.path.join(root_folder, "_XDELTA", "xdelta3.exe")
        self.xdelta60_file = "ctr-u_Online60.xdelta"
        self.xdelta30_file = "ctr-u_Online30.xdelta"
        self.rom_file_path = settings.game_rom  
        #os.path.join(root_folder, "_ROM", "CTR.bin")
        self.patched60_file_path = os.path.join(root_folder, "_ROM", "CTR_Online60.bin")
        self.patched30_file_path = os.path.join(root_folder, "_ROM", "CTR_Online30.bin")
        self.client_path = os.path.join(root_folder, "_CTRClient", "client.exe")
        self.fast_boot = settings.fast_boot
        self.fullscreen = settings.fullscreen
        self.duckstation_path = settings.duckstation
        self.frame_rate = settings.frame_rate
        self.name = settings.name
        self.gui = gui
        self.patched_file = None

        if int(self.frame_rate) == 0:
            self.xdelta_file = self.xdelta30_file
            self.patched_file = self.patched30_file_path
        elif int(self.frame_rate) == 1:
            self.xdelta_file = self.xdelta60_file
            self.patched_file = self.patched60_file_path


    def print_logs(self, text, format=0):
        # format 0 = normal; 1 = red
        # I hope someone will make this better
        if format == 0:
            self.gui.logs_text.append(text)
            self.gui.update()
            
        elif format == 1:
            self.gui.logs_text.append("<div style=\"background-color: red; color:white\">{}</div>".format(text))
            self.gui.update()
        
        
    def patch_game(self):
        if os.path.exists(self.patched_file):
            os.remove(self.patched_file)
        try:
            xdelta_file_path = os.path.join(self.root_folder, "_XDELTA", self.xdelta_file)
            command = f'"{self.xdelta_path}" -d -s "{self.rom_file_path}" "{xdelta_file_path}" "{self.patched_file}"'
            subprocess.run(command, shell=True)
            self.print_logs("Game patched successfully")
        except Exception as e:
            self.print_logs("Error patching the game", 1)
            self.print_logs(str(e), 1)
        
        
    def get_local_version(self):
        try:
            with open("version", "r") as file:
                version = file.read()
                return version
        except Exception as e:
            print(e)
            return "1"
        
    
    def download_file(self, url, destination):
        try:
            self.gui.progress_bar.show()
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
        
            with open(destination, "wb") as file:
                for data in response.iter_content(chunk_size=1024):
                    file.write(data)
                    downloaded_size += len(data)
                    progress = int(100 * downloaded_size / total_size)
                    self.gui.progress_bar.setValue(progress)

        except Exception as e:
            print(e)
    
    
    def download_and_extract_zip(self, url, extract_to, new_file_name):
        temp_zip_path = "temp.zip"
        self.download_file(url, temp_zip_path)
    
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall("temp_folder")
    
        for root, dirs, files in os.walk("temp_folder"):
            for file in files:
                if file.endswith(".exe"):
                    source_file_path = os.path.join(root, file)
                    destination_file_path = os.path.join(extract_to, new_file_name)
                    shutil.move(source_file_path, destination_file_path)
    
        os.remove(temp_zip_path)
        shutil.rmtree("temp_folder")
    
    
    def download_updated_files(self, version):
        self.print_logs("Downloading updated files...")
        self.print_logs("Downloading ctr-u_Online30.xdelta")
        self.download_file(URL_XDELTA_30, "_XDELTA/ctr-u_Online30.xdelta")
        self.print_logs("Downloading ctr-u_Online60.xdelta")
        self.download_file(URL_XDELTA_60, "_XDELTA/ctr-u_Online60.xdelta")
        self.print_logs("Downloading client.exe")
        self.download_and_extract_zip(URL_CLIENT, "_CTRClient", "client.exe")
    
        try:
            with open("version", "w") as file:
                file.write(version)
        except Exception as e:
            print(e)
    
    
    def get_current_patch(self):
        url = URL_CURRENT_VERSION
        response = requests.get(url)
        if response.status_code == 200:
            content = response.text
            return content
        else:
            return "1"
    
    
    def check_for_updates(self):
        self.print_logs("Checking for updates...")
        try:
            local_version = self.get_local_version()
            version = self.get_current_patch()
            if version != local_version:
                self.print_logs(f"Local version: {local_version}\nOnlineCTR version: {version}")
                return True, version
            else:
                self.print_logs(f"Local version: {local_version}\nOnlineCTR version: {version}")
                return False, None
        except Exception as e:
            print(e)
            return False, None
    
    
    def launch_duckstation(self):
        try:
            if os.path.exists(self.patched_file):
                process = f'start "" "{self.duckstation_path}" {self.patched_file}{" -fullscreen" if self.fullscreen == "1" else ""}{" -fastboot" if self.fast_boot == "1" else ""}'
                
                subprocess.Popen(process, shell=True)
                return True
            else:
                self.print_logs("Patched game not found\nTrying to patch the game...")
                self.patch_game()
                return False
        except Exception as e:
            print(e)
            return False


    def check_for_patched_game(self):
        if os.path.exists(self.patched_file):
            return True
        else:
            return False


    def get_news(self):
        # TEST IGNORE THIS
        url = "https://pastebin.com/raw/ARscS0et"
        response = requests.get(url)
        if response.status_code == 200:
            content = response.text
            self.print_logs(f"{content}/n")


    def check_for_files(self):
        if not os.path.exists(self.xdelta_path):
            self.print_logs("xdelta3.exe not found", 1)
            return False
        if not os.path.exists(self.client_path):
            self.print_logs("client.exe not found", 1)
            return False
        if not os.path.exists(self.duckstation_path):
            print(self.duckstation_path)
            self.print_logs("DuckStation not found, please check your settings.ini", 1)
            return False
        if not os.path.exists(self.rom_file_path):
            self.print_logs("CTR.bin not found, please check your _ROM folder", 1)
            return False
        return True
    
    
    def launch_game(self):
        #self.get_news()
        
        #Check for files
        if not self.check_for_files():
            self.print_logs("Some files are missing, please check if your antivirus deleted them...")
            return
        
        is_update, version = self.check_for_updates()
        if is_update:
            self.download_updated_files(version)
            self.patch_game()
        else:
            self.print_logs("No updates found...")
            
        if not self.check_for_patched_game():
            self.print_logs("Patched game not found...")
            self.patch_game()
        
        #Launch DuckStation
        self.print_logs("Launching DuckStation...")
        if not self.launch_duckstation():
            self.print_logs("Error launching DuckStation", 1)
            return
        
        #Launch CTRClient
        self.print_logs("Launching CTRClient...")
        threading.Thread(target=self.launch_game_thread).start()
    
    
    def launch_game_thread(self):
        try:
            os.environ['netname'] = self.name
    
            # 5 seconds delay before launching the client
            command1 = 'timeout /t 5 /nobreak > NUL'
            
            netname = os.environ['netname'].strip()
            command2 = 'echo ' + netname + ' | "' + self.client_path + '"'
            subprocess.call(command1, shell=True)
    
            process = subprocess.Popen(command2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            while True:
                output = process.stdout.readline()
                if output:
                    output = output.decode('utf-8', errors='replace').strip()
                    # Trying to make the logs look better ¯\_(ツ)_/¯
                    output = re.sub(r'[^a-zA-Z0-9: "().@]', '', output)
                    
                    if output.strip() == 'Enter Server IPV4 Address:':
                        self.print_logs("Private lobbies are not supported", 1)
                        self.print_logs("Exiting in 5 seconds...")
                        time.sleep(5)
                        LauncherGUI.kill_process(self)
                        break
                        
                    elif output.strip() != '':
                        self.gui.logs_text.append(output)
        except Exception as e:
            self.print_logs("Error launching CTRClient")
            self.print_logs(str(e))


class MovableWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.m_drag = False
        self.m_DragPosition = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.m_drag = True
            self.m_DragPosition = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.m_drag:
            self.move(event.globalPos() - self.m_DragPosition)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.m_drag = False


class SettingsWindow(MovableWindow):
    def __init__(self, launcher_settings):
        super().__init__()
        self.launcher_settings = launcher_settings
        self.setWindowTitle("CTR Launcher Settings")
        self.setWindowIcon(QIcon('assets/icon.ico'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.resize(300, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint & ~Qt.WindowMinimizeButtonHint)
        layout = QVBoxLayout(central_widget)

        self.create_name_input(layout)
        self.create_frame_rate_input(layout)
        self.create_fast_boot_input(layout)
        self.create_fullscreen_input(layout)
        self.create_duckstation_input(layout)
        self.create_game_rom_input(layout)
        self.create_save_button(layout)

    def create_name_input(self, layout):
        self.name_label = QLabel("Player Name:")
        self.name_input = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        self.name_input.setText(self.launcher_settings.get_player_name())

    def create_frame_rate_input(self, layout):
        self.frame_rate_label = QLabel("Frame Rate:")
        self.frame_rate_input = QComboBox()
        self.frame_rate_input.addItem("30fps")
        self.frame_rate_input.addItem("60fps")
        self.frame_rate_input.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.frame_rate_label)
        layout.addWidget(self.frame_rate_input)
        if self.launcher_settings.get_frame_rate() == "0":
            self.frame_rate_input.setCurrentIndex(0)
        else:
            self.frame_rate_input.setCurrentIndex(1)

    def create_fast_boot_input(self, layout):
        self.fast_boot_label = QLabel("Fast Boot:")
        self.fast_boot_input = QComboBox()
        self.fast_boot_input.addItem("Disabled")
        self.fast_boot_input.addItem("Enabled")
        self.fast_boot_input.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.fast_boot_label)
        layout.addWidget(self.fast_boot_input)
        if self.launcher_settings.get_fast_boot() == "0":
            self.fast_boot_input.setCurrentIndex(0)
        else:
            self.fast_boot_input.setCurrentIndex(1)

    def create_fullscreen_input(self, layout):
        self.fullscreen_label = QLabel("Fullscreen:")
        self.fullscreen_input = QComboBox()
        self.fullscreen_input.addItem("Disabled")
        self.fullscreen_input.addItem("Enabled")
        self.fullscreen_input.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.fullscreen_label)
        layout.addWidget(self.fullscreen_input)
        if self.launcher_settings.get_fullscreen() == "0":
            self.fullscreen_input.setCurrentIndex(0)
        else:
            self.fullscreen_input.setCurrentIndex(1)

    def create_duckstation_input(self, layout):
        self.duckstation_label = QLabel("Duckstation Path:")
        self.duckstation_input = QLineEdit()
        self.duckstation_button = QPushButton("Browse for Duckstation")
        self.duckstation_button.setCursor(Qt.PointingHandCursor)
        self.duckstation_button.clicked.connect(self.browse_duckstation)
        layout.addWidget(self.duckstation_label)
        layout.addWidget(self.duckstation_input)
        layout.addWidget(self.duckstation_button)
        self.duckstation_input.setDisabled(True)
        self.duckstation_input.setText(self.launcher_settings.get_duckstation_path())

    def create_game_rom_input(self, layout):
        self.game_rom_label = QLabel("Game ROM Path:")
        self.game_rom_input = QLineEdit()
        self.game_rom_button = QPushButton("Browse for CTR ROM")
        self.game_rom_button.setCursor(Qt.PointingHandCursor)
        self.game_rom_button.clicked.connect(self.browse_game_rom)
        layout.addWidget(self.game_rom_label)
        layout.addWidget(self.game_rom_input)
        layout.addWidget(self.game_rom_button)
        self.game_rom_input.setDisabled(True)
        self.game_rom_input.setText(self.launcher_settings.get_game_rom_path())

    def create_save_button(self, layout):
        layout.addSpacing(10)
        save_button = QPushButton("Save and Close")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setStyleSheet("background-color: #4CAF50; color: white; border: none; padding: 10px 24px; text-align: center; text-decoration: none; font-size: 16px; margin: 4px 2px;")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

    def save_settings(self):
        self.launcher_settings.name = self.name_input.text()
        self.launcher_settings.frame_rate = str(self.frame_rate_input.currentIndex())
        self.launcher_settings.fast_boot = str(self.fast_boot_input.currentIndex())
        self.launcher_settings.fullscreen = str(self.fullscreen_input.currentIndex())
        self.launcher_settings.duckstation = self.duckstation_input.text()
        self.launcher_settings.game_rom = self.game_rom_input.text()
        self.launcher_settings.save_settings()
        settings = LauncherSettings()
        self.close()

    def browse_duckstation(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Duckstation", filter="duckstation-qt-x64-ReleaseLTCG.exe")
        if file:
            self.duckstation_input.setText(file)

    def browse_game_rom(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Game ROM", filter="*.bin")
        if file:
            self.game_rom_input.setText(file)


class LauncherGameRunnable(QRunnable):
    def __init__(self, game_launcher):
        super().__init__()
        self.game_launcher = game_launcher

    def run(self):
        self.game_launcher.launch_game()        


class HoverButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
        """)
        self.glow_enabled = False

    def enterEvent(self, event):
        if not self.graphicsEffect():
            glow_effect = QGraphicsDropShadowEffect(self)
            glow_effect.setColor(QColor(255, 255, 255)) 
            glow_effect.setOffset(0, 0)
            glow_effect.setBlurRadius(10)
            self.setGraphicsEffect(glow_effect)
        self.update()

    def leaveEvent(self, event):
        self.setGraphicsEffect(None)
        self.update()
        
class LauncherGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.window = self.create_main_window()
        self.logs_text = self.create_logs_textbox()
        self.create_launch_button()
        self.create_settings_button()
        self.create_exit_button()
        self.progress_bar = self.create_progress_bar()

    def create_main_window(self):
        window = MovableWindow()
        window.setAttribute(Qt.WA_TranslucentBackground, True)
        window.setAttribute(Qt.WA_NoSystemBackground, True)
        window.setWindowFlags(Qt.FramelessWindowHint)
        window.setWindowIcon(QIcon('assets/icon.ico'))

        label = QLabel(window)
        pixmap = QPixmap('assets/launcher.png')
        label.setPixmap(pixmap)
        label.setGeometry(0, 0, pixmap.width(), pixmap.height())

        window.label = label
        window.resize(pixmap.width(), pixmap.height())

        return window

    def create_logs_textbox(self):
        logs_textbox = QTextEdit(self.window)
        logs_textbox.setGeometry(315, 70, 450, 260)
        logs_textbox.setText(f"Launcher Version: {LAUNCHER_VERSION}\n")
        logs_textbox.setReadOnly(True)
        logs_textbox.setLineWrapMode(QTextEdit.WidgetWidth)
        logs_textbox.setStyleSheet("background-color: black; color: white; font-family: Arial; font-size: 12px; border-radius: 10px; padding: 10px;")

        return logs_textbox

    def create_launch_button(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        start_path = os.path.join(script_dir, 'assets', 'START.png').replace(os.sep, '/')
        button_launch = HoverButton(self.window)
        button_launch.setGeometry(30, 253, 250, 40)
        button_launch.setStyleSheet(f"""
            HoverButton {{
                border: none;
                background-image: url({start_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """)
        button_launch.setCursor(Qt.PointingHandCursor)
        #debugpy.debug_this_thread()
        button_launch.clicked.connect(self.launch_game_in_thread)

    def create_settings_button(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        settings_path = os.path.join(script_dir, 'assets', 'OPTIONS.png').replace(os.sep, '/')
        button_settings = HoverButton(self.window)
        button_settings.setGeometry(68, 298, 170, 40)
        button_settings.setStyleSheet(f"""
            HoverButton {{
                border: none;
                background-image: url({settings_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """)
        button_settings.setCursor(Qt.PointingHandCursor)
        
        launcher_settings = LauncherSettings()
        self.second_window = SettingsWindow(launcher_settings)
        button_settings.clicked.connect(self.second_window.show)

    def create_exit_button(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        exit_path = os.path.join(script_dir, 'assets', 'EXIT.png').replace(os.sep, '/')
        button_exit = HoverButton(self.window)
        button_exit.setGeometry(85, 340, 140, 30)
        button_exit.setStyleSheet(f"""
            HoverButton {{
                border: none;
                background-image: url({exit_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """)
        button_exit.setCursor(Qt.PointingHandCursor)
        button_exit.clicked.connect(self.close)

    def create_progress_bar(self):
        progress_bar = QProgressBar(self.window)
        progress_bar.setGeometry(315, 348, 450, 20)
        progress_bar.setValue(0)
        progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                background-color: white;
                text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #4CAF50;
                    }""")
        progress_bar.setRange(0, 100)
        progress_bar.hide()
        
        return progress_bar

    def launch_game_in_thread(self):
        runnable = LauncherGameRunnable(GameLauncher(root_folder, self, settings))
        QThreadPool.globalInstance().start(runnable)

    def show(self):
        self.window.show()

    def kill_process(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] in ['client.exe', 'duckstation-qt-x64-ReleaseLTCG.exe']:
                proc.kill()

    def close(self):
        self.kill_process()
        self.destroy()
        sys.exit(0)
        

root_folder = application_path
settings = LauncherSettings()
app = QApplication(sys.argv)
launcher = LauncherGUI()
launcher.show()
sys.exit(app.exec_())