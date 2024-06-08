import configparser
import os
import re
import subprocess
import sys
import threading
from tkinter import Tk, Label, Image
import warnings
import psutil

import requests
from PIL import Image, ImageEnhance, ImageTk

import customtkinter

warnings.filterwarnings('ignore')

LAUNCHER_VERSION = "1.2"
URL_VERSION = "https://github.com/xlenore/OnlineCTR_Launcher/raw/main/version"
URL_CLIENT = "https://github.com/xlenore/OnlineCTR_Launcher/raw/main/_CTRClient/Client.exe"
URL_XDELTA_30 = "https://github.com/xlenore/OnlineCTR_Launcher/raw/main/_XDELTA/ctr-u_Online30.xdelta"
URL_XDELTA_60 = "https://github.com/xlenore/OnlineCTR_Launcher/raw/main/_XDELTA/ctr-u_Online60.xdelta"


if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(os.path.realpath(sys.executable))
elif __file__:
    application_path = os.path.dirname(__file__)

#Kill launcher.exe if already running
current_pid = os.getpid()
for proc in psutil.process_iter(['pid', 'name']):
    if proc.info['name'] == 'launcher.exe' and proc.info['pid'] != current_pid:
        proc.kill()


class LauncherSettings:
    def __init__(self):
        self.config = configparser.ConfigParser(inline_comment_prefixes=";")
        try:
            self.config.read("settings.ini")
            self.name = self.config["SETTINGS"]["name"].strip('"')
            self.game_mode = self.config["SETTINGS"]["game_mode"].strip('"')
            self.duckstation = self.config["PATHS"]["duckstation"].strip('"')
            self.fullscreen = self.config["SETTINGS"]["fullscreen"].strip('"')
            self.fast_boot = self.config["SETTINGS"]["fast_boot"].strip('"')
        except Exception as e:
            self.name = "YourName"
            self.game_mode = "0"
            self.duckstation = r"C:\Users\[yourUserName]\[remaining path to duckstation folder]\duckstation-qt-x64-ReleaseLTCG.exe"
            self.fullscreen = "0"
            self.fast_boot = "0"
            self.save_settings()
            
    def save_settings(self):
        self.config["SETTINGS"] = {
            "name": f'"{self.name}" ; Your name in the game',
            "game_mode": f'{self.game_mode} ; 0 = 30fps, 1 = 60fps',
            "fullscreen": f'{self.fullscreen} ; 0 = disabled, 1 = enabled',
            "fastboot": f'{self.fast_boot} ; 0 = disabled, 1 = enabled'
        }
        self.config["PATHS"] = {
            "duckstation": f'"{self.duckstation}"'
        }
        with open("settings.ini", "w") as file:
            self.config.write(file)


class GameLauncher:
    def __init__(self, root_folder, gui, settings):
        self.root_folder = root_folder
        self.xdelta_path = os.path.join(root_folder, "_XDELTA", "xdelta3.exe")
        self.xdelta60_file = "ctr-u_Online60.xdelta"
        self.xdelta30_file = "ctr-u_Online30.xdelta"
        self.rom_file_path = os.path.join(root_folder, "_ROM", "CTR.bin")
        self.patched60_file_path = os.path.join(root_folder, "_ROM", "CTR_Online60.bin")
        self.patched30_file_path = os.path.join(root_folder, "_ROM", "CTR_Online30.bin")
        self.client_path = os.path.join(root_folder, "_CTRClient", "Client.exe")
        self.fast_boot = settings.fast_boot
        self.fullscreen = settings.fullscreen
        self.duckstation_path = settings.duckstation
        self.game_mode = settings.game_mode
        self.name = settings.name
        self.gui = gui
        self.patched_file = None

        if int(self.game_mode) == 0:
            self.xdelta_file = self.xdelta30_file
            self.patched_file = self.patched30_file_path
        elif int(self.game_mode) == 1:
            self.xdelta_file = self.xdelta60_file
            self.patched_file = self.patched60_file_path


    def print_logs(self, text):
        self.gui.logs_text.after(0, self.gui.logs_text.insert, "end", text + "\n")
        self.gui.logs_text.see("end")
        self.gui.update()
        
        
    def patch_game(self):
        if os.path.exists(self.patched_file):
            os.remove(self.patched_file)
        xdelta_file_path = os.path.join(self.root_folder, "_XDELTA", self.xdelta_file)
        command = f'"{self.xdelta_path}" -d -s "{self.rom_file_path}" "{xdelta_file_path}" "{self.patched_file}"'
        subprocess.run(command, shell=True)
        
        
    def get_local_version(self):
        try:
            with open("version", "r") as file:
                version = file.read()
                return version
        except Exception as e:
            print(e)
            return "1.0"
        
    
    def download_updated_files(self):
        self.print_logs("Downloading updated files...")
        try:
            response = requests.get(URL_XDELTA_30)
            with open("_XDELTA/ctr-u_Online30.xdelta", "wb") as file:
                file.write(response.content)
                
            response = requests.get(URL_XDELTA_60)
            with open("_XDELTA/ctr-u_Online60.xdelta", "wb") as file:
                file.write(response.content)
                
            response = requests.get(URL_CLIENT)
            with open("_CTRClient/Client.exe", "wb") as file:
                file.write(response.content)
                
            response = requests.get(URL_VERSION)
            with open("version", "w") as file:
                file.write(response.text)
                
        except Exception as e:
            print(e)
    
    
    def check_for_updates(self):
        self.print_logs("Checking for updates...")
        try:
            local_version = self.get_local_version()
            response = requests.get(URL_VERSION)
            version = response.text
            if version != local_version:
                self.print_logs(f"Local version: {local_version}\nGitHub version: {version}")
                return True
            else:
                self.print_logs(f"Local version: {local_version}\nGitHub version: {version}")
                return False
        except Exception as e:
            print(e)
            return False
    
    
    def launch_duckstation(self):
        try:
            if os.path.exists(os.path.join(root_folder, self.patched_file)):
                process = f'start "" {self.duckstation_path} {self.patched_file}{" -fullscreen" if self.fullscreen == "1" else ""}{" -fastboot" if self.fast_boot == "1" else ""}'
                subprocess.Popen(process, shell=True)
            else:
                self.print_logs("Patched game not found")
        except Exception as e:
            print(e)


    def check_for_patched_game(self):
        if os.path.exists(self.patched_file):
            return True
        else:
            return False


    def check_for_files(self):
        if not os.path.exists(self.xdelta_path):
            self.print_logs("xdelta3.exe not found")
            return False
        if not os.path.exists(self.client_path):
            self.print_logs("Client.exe not found")
            return False
        if not os.path.exists(self.duckstation_path):
            print(self.duckstation_path)
            self.print_logs("DuckStation not found, please check your settings.ini")
            return False
        if not os.path.exists(self.rom_file_path):
            self.print_logs("CTR.bin not found, please check your _ROM folder")
            return False
        return True
    
    
    def launch_game(self):
        #Check for files
        if not self.check_for_files():
            self.print_logs("Some files are missing, please check if your antivirus deleted them...")
            return
        
        is_update = self.check_for_updates()
        if is_update:
            self.download_updated_files()
            self.patch_game()
        else:
            self.print_logs("No updates found...")
            
        if not self.check_for_patched_game():
            self.print_logs("Patched game not found...")
            self.patch_game()
        
        #Launch DuckStation
        self.print_logs("Launching DuckStation...")
        self.launch_duckstation()
        
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
                if output == b'' and process.poll() is not None:
                    break
                if output:
                    output = output.decode('utf-8', errors='replace').strip()
                    # Trying to make the logs look better ¯\_(ツ)_/¯
                    output = re.sub(r'[^a-zA-Z0-9: "().@]', '', output)
                        
                    self.gui.logs_text.after(0, self.gui.logs_text.insert, "end", output + "\n")
                    self.gui.logs_text.see("end")
        except Exception as e:
            self.print_logs("Error launching CTRClient")
            self.print_logs(str(e))


class CTkImage(ImageTk.PhotoImage):
    def __init__(self, image=None, **kwargs):
        super().__init__(image, **kwargs)
        self._image = image

    def __getattr__(self, name):
        return getattr(self._image, name)


class GameLauncherGUI(customtkinter.CTk):
    def __init__(self, game_launcher):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.iconpath = CTkImage(file='assets\\icon.ico')
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)

        self.title(f"OnlineCTR Launcher [UNOFFICIAL] | v{LAUNCHER_VERSION}")
        self.geometry("800x350")
        self.resizable(False, False)
        self.game_launcher = game_launcher
    
    def kill_process(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] in ['Client.exe', 'duckstation-qt-x64-ReleaseLTCG.exe']:
                proc.kill()
    
    def on_close(self):
        self.kill_process()
        self.destroy()
        sys.exit(0)
    
    def create_widgets(self):
        #Background
        background_path = "assets/background.png"
        self.background_image = Image.open(background_path)
        self.background_image = self.background_image.convert("RGBA")
        self.background_image = self.background_image.resize((800, 350), Image.LANCZOS)

        #Logo
        logo_path = "assets/icon.png"
        self.logo_image = Image.open(logo_path)
        self.logo_image = self.logo_image.convert("RGBA")
        self.logo_image = self.logo_image.resize((800, 350), Image.LANCZOS)

        #Combine
        self.combined_image = Image.alpha_composite(self.background_image, self.logo_image)
        self.combined_image_tk = CTkImage(self.combined_image)
        self.background_label = customtkinter.CTkLabel(self, image=self.combined_image_tk)
        self.background_label.place(x=0, y=0)
        
        
        #Launch Button
        self.game_launcher_button = customtkinter.CTkButton(self, text="Launch Game", font=("", 30),
                                                fg_color="#951A02", hover_color="#FFC432", border_color="#EE6518",
                                                border_width=2, width=150, height=50,
                                                command=game_launcher.launch_game)
        self.game_launcher_button.place(x=550, y=250)
        
        #Logs
        self.logs_text = customtkinter.CTkTextbox(self, font=("", 12),
                                                width=480, height=250, border_color="#000000", border_width=2)
        self.logs_text.place(x=10, y=50)


root_folder = application_path
game_launcher_gui = GameLauncherGUI(None)
settings = LauncherSettings()
game_launcher = GameLauncher(root_folder, game_launcher_gui, settings)

game_launcher_gui.game_launcher = game_launcher

game_launcher_gui.create_widgets()
game_launcher_gui.mainloop()