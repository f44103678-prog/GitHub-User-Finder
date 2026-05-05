import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
from threading import Thread

# ---------------------------- Data Management ----------------------------
class FavoritesManager:
    def __init__(self, filename="favorites.json"):
        self.filename = filename
        self.favorites = []  # list of dicts: {"login": "...", "avatar_url": "...", "html_url": "..."}
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.favorites = json.load(f)
            except:
                self.favorites = []

    def save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.favorites, f, ensure_ascii=False, indent=2)

    def add(self, user):
        # user: dict with login, avatar_url, html_url
        if not any(fav["login"] == user["login"] for fav in self.favorites):
            self.favorites.append(user)
            self.save()
            return True
        return False

    def remove(self, login):
        self.favorites = [fav for fav in self.favorites if fav["login"] != login]
        self.save()

    def is_favorite(self, login):
        return any(fav["login"] == login for fav in self.favorites)

    def get_all(self):
        return self.favorites

# ---------------------------- GitHub API ----------------------------
class GitHubAPI:
    @staticmethod
    def search_users(query):
        """Return list of user dicts or None if error."""
        if not query.strip():
            return []
        url = f"https://api.github.com/search/users?q={query}&per_page=20"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                users = []
                for item in data.get("items", []):
                    users.append({
                        "login": item["login"],
                        "avatar_url": item["avatar_url"],
                        "html_url": item["html_url"]
                    })
                return users
            else:
                return None
        except requests.exceptions.RequestException:
            return None

# ---------------------------- GUI Application ----------------------------
class GitHubUserFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GitHub User Finder")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.fav_manager = FavoritesManager()
        self.current_results = []  # list of user dicts from last search

        self._setup_ui()
        self._refresh_favorites_display()

    def _setup_ui(self):
        # ----- Search frame -----
        search_frame = ttk.LabelFrame(self.root, text="Поиск пользователей GitHub", padding=10)
        search_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(search_frame, text="Имя пользователя:").pack(side="left", padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.search_users())

        self.search_btn = ttk.Button(search_frame, text="Поиск", command=self.search_users)
        self.search_btn.pack(side="left", padx=5)

        self.status_label = ttk.Label(search_frame, text="", foreground="blue")
        self.status_label.pack(side="left", padx=10)

        # ----- Results frame (listbox + scrollbar) -----
        results_frame = ttk.LabelFrame(self.root, text="Результаты поиска", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)

        list_frame = ttk.Frame(results_frame)
        list_frame.pack(fill="both", expand=True)

        self.results_listbox = tk.Listbox(list_frame, height=10, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.results_listbox.yview)
        self.results_listbox.config(yscrollcommand=scrollbar.set)
        self.results_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Buttons below results
        btn_frame = ttk.Frame(results_frame)
        btn_frame.pack(fill="x", pady=5)

        self.add_fav_btn = ttk.Button(btn_frame, text="★ Добавить в избранное", command=self.add_to_favorites)
        self.add_fav_btn.pack(side="left", padx=5)

        self.open_profile_btn = ttk.Button(btn_frame, text="Открыть профиль в браузере", command=self.open_profile)
        self.open_profile_btn.pack(side="left", padx=5)

        # ----- Favorites frame -----
        fav_frame = ttk.LabelFrame(self.root, text="Избранные пользователи", padding=10)
        fav_frame.pack(fill="both", expand=True, padx=10, pady=5)

        fav_list_frame = ttk.Frame(fav_frame)
        fav_list_frame.pack(fill="both", expand=True)

        self.fav_listbox = tk.Listbox(fav_list_frame, height=8, font=("Consolas", 10))
        fav_scrollbar = ttk.Scrollbar(fav_list_frame, orient="vertical", command=self.fav_listbox.yview)
        self.fav_listbox.config(yscrollcommand=fav_scrollbar.set)
        self.fav_listbox.pack(side="left", fill="both", expand=True)
        fav_scrollbar.pack(side="right", fill="y")

        fav_btn_frame = ttk.Frame(fav_frame)
        fav_btn_frame.pack(fill="x", pady=5)

        self.remove_fav_btn = ttk.Button(fav_btn_frame, text="Удалить из избранного", command=self.remove_from_favorites)
        self.remove_fav_btn.pack(side="left", padx=5)

        self.open_fav_btn = ttk.Button(fav_btn_frame, text="Открыть профиль", command=self.open_favorite_profile)
        self.open_fav_btn.pack(side="left", padx=5)

    def search_users(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showerror("Ошибка", "Поле поиска не может быть пустым!")
            return

        self.status_label.config(text="Поиск...")
        self.search_btn.config(state="disabled")
        self.results_listbox.delete(0, tk.END)
        self.current_results = []

        # Run API call in thread to avoid freezing GUI
        def thread_target():
            users = GitHubAPI.search_users(query)
            self.root.after(0, self._on_search_complete, users)

        Thread(target=thread_target, daemon=True).start()

    def _on_search_complete(self, users):
        self.search_btn.config(state="normal")
        if users is None:
            self.status_label.config(text="Ошибка сети или API. Проверьте подключение.")
            messagebox.showerror("Ошибка", "Не удалось выполнить поиск. Проверьте интернет.")
        elif len(users) == 0:
            self.status_label.config(text="Пользователи не найдены.")
        else:
            self.status_label.config(text=f"Найдено: {len(users)} пользователей")
            self.current_results = users
            for user in users:
                fav_mark = "★ " if self.fav_manager.is_favorite(user["login"]) else "  "
                self.results_listbox.insert(tk.END, f"{fav_mark}{user['login']}")

    def add_to_favorites(self):
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Сначала выберите пользователя из результатов поиска.")
            return
        idx = selection[0]
        user = self.current_results[idx]
        if self.fav_manager.add(user):
            self._refresh_favorites_display()
            # Update star mark in results listbox
            self.results_listbox.delete(idx)
            self.results_listbox.insert(idx, f"★ {user['login']}")
            messagebox.showinfo("Успех", f"Пользователь {user['login']} добавлен в избранное.")
        else:
            messagebox.showinfo("Информация", f"Пользователь {user['login']} уже в избранном.")

    def remove_from_favorites(self):
        selection = self.fav_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите пользователя в списке избранного.")
            return
        login = self.fav_listbox.get(selection[0]).split(" ")[-1]  # format "★ login"
        self.fav_manager.remove(login)
        self._refresh_favorites_display()
        # Update star in results if present
        for i, user in enumerate(self.current_results):
            if user["login"] == login:
                self.results_listbox.delete(i)
                self.results_listbox.insert(i, f"  {login}")
                break
        messagebox.showinfo("Успех", f"Пользователь {login} удалён из избранного.")

    def open_profile(self):
        selection = self.results_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите пользователя из результатов поиска.")
            return
        user = self.current_results[selection[0]]
        import webbrowser
        webbrowser.open(user["html_url"])

    def open_favorite_profile(self):
        selection = self.fav_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите пользователя в списке избранного.")
            return
        login = self.fav_listbox.get(selection[0]).split(" ")[-1]
        favs = self.fav_manager.get_all()
        for fav in favs:
            if fav["login"] == login:
                import webbrowser
                webbrowser.open(fav["html_url"])
                return

    def _refresh_favorites_display(self):
        self.fav_listbox.delete(0, tk.END)
        for fav in self.fav_manager.get_all():
            self.fav_listbox.insert(tk.END, f"★ {fav['login']}")

# ---------------------------- Main ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = GitHubUserFinderApp(root)
    root.mainloop()