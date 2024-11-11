import subprocess
import sys

# Zapewnienie, że `psutil` jest zainstalowane
try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil  # Ponowny import po instalacji

import os
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import json
import time
from datetime import datetime

SAVE_FILE = "bot_paths.json"
LOG_FILE = "logi_uruchomien.json"
ERROR_FILE = "errors.log"

class BotManagerApp:
    def __init__(self, root):
        self.root = root
        self.max_bots = 10
        self.bot_paths = [None] * self.max_bots  # Ścieżki do botów
        self.process_titles = [f"bot_{i + 1}" for i in range(self.max_bots)]  # Unikalne tytuły okien dla każdego bota
        self.logs_frame = None  # Ramka do wyświetlania logów
        self.running_since = [None] * self.max_bots  # Śledzenie czasu uruchomienia dla każdego bota

        self.root.title("Zarządzanie Botami")
        self.create_widgets()
        self.load_bot_paths()
        self.create_logs_panel()

        # Tworzenie pliku logów, jeśli nie istnieje
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'w') as log_file:
                json.dump({}, log_file)

    def create_widgets(self):
        self.bot_frame = tk.Frame(self.root)
        self.bot_frame.pack(pady=10)

        for i in range(self.max_bots):
            bot_label = tk.Label(self.bot_frame, text=f"Bot {i + 1}: ", width=20)
            bot_label.grid(row=i, column=0, padx=5, pady=5)

            edit_button = tk.Button(self.bot_frame, text="✏️", command=lambda i=i: self.edit_bot_name(i))
            edit_button.grid(row=i, column=1, padx=5, pady=5)

            add_file_button = tk.Button(self.bot_frame, text="Dodaj plik .bat", command=lambda i=i: self.add_file(i))
            add_file_button.grid(row=i, column=2, padx=5, pady=5)

            start_button = tk.Button(self.bot_frame, text="Uruchom", command=lambda i=i: self.start_bot(i))
            start_button.grid(row=i, column=3, padx=5, pady=5)

            stop_button = tk.Button(self.bot_frame, text="Zatrzymaj", command=lambda i=i: self.stop_bot(i))
            stop_button.grid(row=i, column=4, padx=5, pady=5)

            restart_button = tk.Button(self.bot_frame, text="Restart", command=lambda i=i: self.restart_bot(i))
            restart_button.grid(row=i, column=5, padx=5, pady=5)

            status_label = tk.Label(self.bot_frame, text="zatrzymany", width=30, fg="red")
            status_label.grid(row=i, column=6, padx=5, pady=5)

            # Dodanie przycisku do aktualizacji za pomocą git pull
            update_button = tk.Button(self.bot_frame, text="Aktualizuj (git pull)", command=lambda i=i: self.update_bot_with_git(i))
            update_button.grid(row=i, column=7, padx=5, pady=5)

            if self.bot_paths[i] is not None and isinstance(self.bot_paths[i], tuple) and self.bot_paths[i][0] is not None:
                self.bot_paths[i] = (self.bot_paths[i][0], status_label, bot_label)
                bot_label.config(text=os.path.basename(self.bot_paths[i][0]))
                self.update_status(i)
            else:
                self.bot_paths[i] = (None, status_label, bot_label)

    def create_logs_panel(self):
        """Tworzy panel do wyświetlania logów aplikacji."""
        self.logs_frame = tk.Frame(self.root)
        self.logs_frame.pack(pady=10)
        logs_label = tk.Label(self.logs_frame, text="Logi Działania", font=("Arial", 12, "bold"))
        logs_label.pack()

        self.logs_text = tk.Text(self.logs_frame, height=10, width=100)
        self.logs_text.pack()
        self.logs_text.insert(tk.END, "Logi aplikacji zostaną wyświetlone tutaj.\n")
        self.logs_text.config(state=tk.DISABLED)

    def load_bot_paths(self):
        """Ładuje zapisane ścieżki do plików botów z pliku JSON."""
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, 'r') as file:
                try:
                    loaded_paths = json.load(file)
                    for i, path_info in enumerate(loaded_paths):
                        if isinstance(path_info, dict) and 'path' in path_info:
                            status_label = tk.Label(self.bot_frame, text="zatrzymany", width=30, fg="red")
                            bot_label = tk.Label(self.bot_frame, text=path_info.get('name', os.path.basename(path_info['path'])), width=20)
                            self.bot_paths[i] = (
                                path_info['path'],
                                status_label,
                                bot_label
                            )
                            bot_label.grid(row=i, column=0, padx=5, pady=5)
                            status_label.grid(row=i, column=6, padx=5, pady=5)
                            self.update_status(i)
                except json.JSONDecodeError:
                    messagebox.showerror("Błąd pliku", "Plik bot_paths.json jest uszkodzony lub ma niepoprawny format.")

    def save_bot_paths(self):
        """Zapisuje ścieżki do plików botów w pliku JSON."""
        paths_to_save = [
            {
                'path': path[0],
                'name': path[2].cget('text') if path is not None else None
            } if path[0] is not None else None
            for path in self.bot_paths
        ]
        with open(SAVE_FILE, 'w') as file:
            json.dump(paths_to_save, file)

    def update_status(self, bot_index):
        """Aktualizuje status bota, sprawdzając, czy jest uruchomiony."""
        if self.bot_paths[bot_index][0] is not None:
            bot_path = os.path.abspath(self.bot_paths[bot_index][0]).lower()
            bot_filename = os.path.basename(bot_path)
            is_running = False

            for proc in psutil.process_iter(attrs=['cmdline', 'name']):
                try:
                    if proc.info['cmdline']:
                        # Sprawdza, czy proces zawiera ścieżkę do pliku bota
                        if any(bot_filename in os.path.basename(arg).lower() for arg in proc.info['cmdline']):
                            is_running = True
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            if is_running:
                self.bot_paths[bot_index][1].config(text="uruchomiony", fg="green")
            else:
                self.bot_paths[bot_index][1].config(text="zatrzymany", fg="red")

    def update_bot_with_git(self, bot_index):
        """Wykonuje git pull, aby zaktualizować katalog bota."""
        if 0 <= bot_index < len(self.bot_paths) and self.bot_paths[bot_index][0] is not None:
            bot_path = self.bot_paths[bot_index][0]
            bot_directory = os.path.dirname(bot_path)

            if os.path.exists(os.path.join(bot_directory, '.git')):
                try:
                    result = subprocess.run(['git', 'pull'], cwd=bot_directory, text=True, capture_output=True, check=True)
                    self.log_action(f"Aktualizacja Bota {bot_index + 1} zakończona: {result.stdout}")
                    messagebox.showinfo("Aktualizacja", f"Aktualizacja Bota {bot_index + 1} zakończona:\n{result.stdout}")
                except subprocess.CalledProcessError as e:
                    self.log_error(f"Błąd aktualizacji Bota {bot_index + 1}: {e.stderr}")
                    messagebox.showerror("Błąd", f"Błąd aktualizacji Bota {bot_index + 1}:\n{e.stderr}")
            else:
                messagebox.showwarning("Brak repozytorium Git", f"Katalog Bota {bot_index + 1} nie jest repozytorium Git.")
        else:
            messagebox.showwarning("Brak bota", "Nie ma skonfigurowanego bota w tym slocie.")

    def log_action(self, message):
        self.logs_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.logs_text.insert(tk.END, log_entry)
        self.logs_text.see(tk.END)
        self.logs_text.config(state=tk.DISABLED)

        with open(LOG_FILE, 'r+') as log_file:
            logs = json.load(log_file)
            logs[timestamp] = message
            log_file.seek(0)
            json.dump(logs, log_file)
            log_file.truncate()

    def add_file(self, bot_index):
        """Pozwala na dodanie pliku .bat do slotu bota."""
        if 0 <= bot_index < self.max_bots:
            file_path = filedialog.askopenfilename(filetypes=[("Batch files", "*.bat")])
            if file_path:
                self.bot_paths[bot_index] = (file_path, self.bot_paths[bot_index][1], self.bot_paths[bot_index][2])
                self.bot_paths[bot_index][2].config(text=os.path.basename(file_path))
                self.bot_paths[bot_index][1].config(text="zatrzymany", fg="red")
                self.save_bot_paths()
                self.update_status(bot_index)
                self.log_action(f"Dodano plik {file_path} dla Bota {bot_index + 1}")
            else:
                messagebox.showwarning("Brak pliku", "Nie wybrano żadnego pliku.")
        else:
            messagebox.showerror("Błąd", "Niepoprawny numer slotu.")

    def stop_bot(self, bot_index):
        """Zatrzymuje działającego bota."""
        if 0 <= bot_index < len(self.bot_paths) and self.bot_paths[bot_index][0] is not None:
            bot_path = os.path.abspath(self.bot_paths[bot_index][0]).lower()
            bot_filename = os.path.basename(bot_path)
            stopped = False

            for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and proc.info['cmdline']:
                        if any(bot_filename in os.path.basename(arg).lower() for arg in proc.info['cmdline']):
                            for child in proc.children(recursive=True):
                                child.kill()
                            proc.kill()
                            stopped = True
                            self.bot_paths[bot_index][1].config(text="zatrzymany", fg="red")
                            self.log_action(f"Zatrzymano Bota {bot_index + 1}")
                            self.running_since[bot_index] = None
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            if not stopped:
                messagebox.showwarning("Nie znaleziono", f"Nie znaleziono uruchomionego procesu dla bota {bot_index + 1}.")
                self.log_action(f"Nie znaleziono uruchomionego procesu dla Bota {bot_index + 1}")
        else:
            messagebox.showwarning("Brak bota", "Nie ma skonfigurowanego bota w tym slocie.")

    def restart_bot(self, bot_index):
        """Restartuje bota, zatrzymując go i uruchamiając ponownie."""
        if 0 <= bot_index < len(self.bot_paths) and self.bot_paths[bot_index][0] is not None:
            self.stop_bot(bot_index)
            retries = 5
            bot_path = os.path.abspath(self.bot_paths[bot_index][0]).lower()

            for _ in range(retries):
                is_running = any(
                    proc.info['cmdline'] and
                    any(bot_path in os.path.abspath(arg).lower() for arg in proc.info['cmdline'] if os.path.isfile(arg))
                    for proc in psutil.process_iter(attrs=['cmdline', 'name'])
                    if proc.info['cmdline']
                )
                if not is_running:
                    break
                time.sleep(0.5)

            if is_running:
                self.log_action(f"Bot {bot_index + 1} nadal działa po kilku próbach zatrzymania.")
                messagebox.showwarning("Niepowodzenie", f"Nie udało się zatrzymać Bota {bot_index + 1}.")
            else:
                self.start_bot(bot_index)
                self.log_action(f"Zrestartowano Bota {bot_index + 1}.")
        else:
            messagebox.showwarning("Brak bota", "Nie ma skonfigurowanego bota w tym slocie.")

    def edit_bot_name(self, bot_index):
        """Pozwala na edycję nazwy bota."""
        if self.bot_paths[bot_index][0] is not None:
            new_name = simpledialog.askstring("Zmień nazwę", f"Podaj nową nazwę dla bota {os.path.basename(self.bot_paths[bot_index][0])}")
            if new_name:
                self.bot_paths[bot_index][2].config(text=new_name)
                self.save_bot_paths()
                self.log_action(f"Zmieniono nazwę Bota {bot_index + 1} na {new_name}")
        else:
            messagebox.showwarning("Brak bota", f"Slot {bot_index + 1} jest pusty. Nie można zmienić nazwy.")

    def start_bot(self, bot_index):
        """Uruchamia plik .bat dla wybranego bota."""
        if 0 <= bot_index < len(self.bot_paths) and self.bot_paths[bot_index][0] is not None:
            window_title = self.process_titles[bot_index] if self.process_titles[bot_index] else ""
            is_already_running = any(
                proc.info['name'] and proc.info['cmdline'] and
                'cmd.exe' in proc.info['name'].lower() and
                window_title.lower() in " ".join(proc.info['cmdline']).lower()
                for proc in psutil.process_iter(attrs=['cmdline', 'name'])
                if proc.info['cmdline']
            )

            if is_already_running:
                messagebox.showinfo("Informacja", f"Bot {bot_index + 1} jest już uruchomiony.")
            else:
                try:
                    bot_path = self.bot_paths[bot_index][0]
                    bot_directory = os.path.dirname(bot_path)
                    subprocess.Popen(f'start cmd /K "title {window_title} & {bot_path}"', cwd=bot_directory, shell=True)
                    self.bot_paths[bot_index][1].config(text="uruchomiony", fg="green")
                    self.log_action(f"Uruchomiono Bota {bot_index + 1} ({bot_path})")
                    self.running_since[bot_index] = time.time()
                    self.update_timer(bot_index)
                except Exception as e:
                    self.log_error(f"Błąd uruchamiania Bota {bot_index + 1}: {e}")
                    messagebox.showerror("Błąd", f"Błąd podczas uruchamiania bota {bot_index + 1}: {e}")
        else:
            messagebox.showwarning("Brak bota", "Nie ma skonfigurowanego bota w tym slocie.")

    def update_timer(self, bot_index):
        """Aktualizuje licznik czasu pracy bota."""
        if self.running_since[bot_index] is not None:
            elapsed_time = int(time.time() - self.running_since[bot_index])
            formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            self.bot_paths[bot_index][1].config(text=f"Uruchomiony ({formatted_time})", fg="green")

            self.root.after(1000, self.update_timer, bot_index)

# Tworzenie interfejsu graficznego
root = tk.Tk()
app = BotManagerApp(root)
root.mainloop()
