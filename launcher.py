import configparser
import os
import re
import subprocess
import sys
import threading
import tkinter

import requests
from PIL import Image, ImageEnhance, ImageTk

import customtkinter

customtkinter.FontManager.load_font("crash-a-like.ttf")

LAUNCHER_VERSION = "1.0"
URL_VERSION = "https://github.com/xlenore/CTROnline_Launcher/raw/main/version"
URL_CLIENT = "https://github.com/xlenore/CTROnline_Launcher/raw/main/_CTRClient/Client.exe"
URL_XDELTA_30 = "https://github.com/xlenore/CTROnline_Launcher/raw/main/_XDELTA/ctr-u_Online30.xdelta"
URL_XDELTA_60 = "https://github.com/xlenore/CTROnline_Launcher/raw/main/_XDELTA/ctr-u_Online60.xdelta"

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(os.path.realpath(sys.executable))
elif __file__:
    application_path = os.path.dirname(__file__)
    

class LauncherSettings:
    def __init__(self):
        self.config = configparser.ConfigParser(inline_comment_prefixes=";")
        self.config.read("settings.ini")
        self.name = self.config["SETTINGS"]["name"]
        self.game_mode = self.config["SETTINGS"]["game_mode"]
        self.duckstation = self.config["PATHS"]["duckstation"]


class GameLauncher:
    def __init__(self, root_folder, gui, settings):
        self.root_folder = root_folder
        self.xdelta_path = os.path.join(root_folder, "_XDELTA", "xdelta3.exe")
        self.xdelta60_file = "ctr-u_Online60.xdelta"
        self.xdelta30_file = "ctr-u_Online30.xdelta"
        self.rom_file = os.path.join(root_folder, "_ROM", "CTR.bin")
        self.patched60_file = os.path.join(root_folder, "_ROM", "CTR_Online60.bin")
        self.patched30_file = os.path.join(root_folder, "_ROM", "CTR_Online30.bin")
        self.client = os.path.join(root_folder, "_CTRClient", "Client.exe")
        self.duckstation = settings.duckstation
        self.game_mode = settings.game_mode
        self.name = settings.name
        self.gui = gui
        self.patched_file = None

        if int(self.game_mode) == 0:
            self.xdelta_file = self.xdelta30_file
            self.patched_file = self.patched30_file
        elif int(self.game_mode) == 1:
            self.xdelta_file = self.xdelta60_file
            self.patched_file = self.patched60_file


    def print_logs(self, text):
        self.gui.logs_text.after(0, self.gui.logs_text.insert, "end", text + "\n")
        self.gui.logs_text.see("end")
        self.gui.update()
        
        
    def patch_game(self):
        if os.path.exists(self.patched_file):
            os.remove(self.patched_file)
        xdelta_file_path = os.path.join(self.root_folder, "_XDELTA", self.xdelta_file)
        command = f'"{self.xdelta_path}" -d -s "{self.rom_file}" "{xdelta_file_path}" "{self.patched_file}"'
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
                process = f'start "" {self.duckstation} {self.patched_file}'
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


    def launch_game(self):
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
            command2 = 'echo ' + netname + ' | ' + self.client
    
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


class GameLauncherGUI(customtkinter.CTk):
    def __init__(self, game_launcher):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.iconpath = ImageTk.PhotoImage(file='assets\\icon.png')
        self.wm_iconbitmap()
        self.iconphoto(False, self.iconpath)

        self.title(f"CTR Online Game Launcher [UNOFFICIAL] | v{LAUNCHER_VERSION}")
        self.geometry("800x350")
        self.resizable(False, False)
        self.game_launcher = game_launcher
        
    def on_close(self):
        os.system("taskkill /f /im Client.exe")
        os.system("taskkill /f /im duckstation-qt-x64-ReleaseLTCG.exe")
        self.destroy()
        sys.exit(0)
    
    def create_widgets(self):
        #Background
        current_path = os.path.dirname(os.path.realpath(__file__))
        img = Image.open(current_path + "\\assets\\background.png")

        enhancer = ImageEnhance.Brightness(img)
        darker_img = enhancer.enhance(0.5)
        
        self.bg_image = customtkinter.CTkImage(darker_img, size=(800, 350))
        self.bg_image_label = customtkinter.CTkLabel(self, text=None, image=self.bg_image)
        self.bg_image_label.place(x=0, y=0)
        
        #Logo

        logo_img = Image.open(current_path + "\\assets\\icon.png")
        self.logo_img = customtkinter.CTkImage(logo_img, size=(200, 200))
        self.logo_img_label = customtkinter.CTkLabel(self, text=None, image=self.logo_img, bg_color="transparent")
        self.logo_img_label.place(x=550, y=25)
        
        
        #Launch Button
        self.game_launcher_button = customtkinter.CTkButton(self, text="Launch Game", font=("crash-a-like", 30),
                                                fg_color="#951A02", hover_color="#FFC432", border_color="#EE6518",
                                                border_width=2, width=150, height=50,
                                                command=game_launcher.launch_game)
        self.game_launcher_button.place(x=650, y=300)
        
        #Logs
        self.logs_text = customtkinter.CTkTextbox(self, font=("", 12),
                                                width=480, height=250)
        self.logs_text.place(x=10, y=50)


root_folder = application_path
game_launcher_gui = GameLauncherGUI(None)
settings = LauncherSettings()
game_launcher = GameLauncher(root_folder, game_launcher_gui, settings)

game_launcher_gui.game_launcher = game_launcher

game_launcher_gui.create_widgets()
game_launcher_gui.logs_text.after(0, game_launcher_gui.logs_text.insert, "end", "CTROnline Launcher by: xlenore\n")
game_launcher_gui.mainloop()