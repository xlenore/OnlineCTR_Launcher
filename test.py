class GameLauncherGUI(customtkinter.CTk):
    def __init__(self, game_launcher):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Configurar ventana
        self.title(f"OnlineCTR Launcher [UNOFFICIAL] | v{LAUNCHER_VERSION}")
        self.geometry("800x350")
        self.resizable(False, False)

        # Icono de la ventana
        icon_path = "assets/icon.png"
        self.iconphoto(True, PhotoImage(file=icon_path))

        self.game_launcher = game_launcher

        # Cargar y combinar imágenes
        self.load_images()

        # Crear widgets
        self.create_widgets()

    def on_close(self):
        os.system("taskkill /f /im Client.exe")
        os.system("taskkill /f /im duckstation-qt-x64-ReleaseLTCG.exe")
        self.destroy()
        sys.exit(0)

    def load_images(self):
        # Cargar imagen de fondo
        background_path = "assets/background.png"
        self.background_image = Image.open(background_path)
        self.background_image = self.background_image.convert("RGBA")

        # Cargar imagen del logo
        logo_path = "assets/icon.png"
        self.logo_image = Image.open(logo_path)
        self.logo_image = self.logo_image.convert("RGBA")

        # Combinar imágenes
        self.combined_image = Image.alpha_composite(self.background_image, self.logo_image)

    def create_widgets(self):
        # Mostrar imagen combinada en un Label
        self.combined_photo = ImageTk.PhotoImage(self.combined_image)
        self.background_label = customtkinter.CTkLabel(self, image=self.combined_photo)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Botón de lanzamiento del juego
        self.launch_button = customtkinter.CTkButton(self, text="Launch Game", font=("crash-a-like", 30),
                                                    fg_color="#951A02", hover_color="#FFC432", border_color="#EE6518",
                                                    border_width=2, width=150, height=50,
                                                    command=self.game_launcher.launch_game)
        self.launch_button.place(x=550, y=250)

        # Área de texto para los logs
        self.logs_text = customtkinter.CTkTextbox(self, font=("", 12), width=480, height=250)
        self.logs_text.place(x=10, y=50)