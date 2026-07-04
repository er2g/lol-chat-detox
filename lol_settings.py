# -*- coding: utf-8 -*-
"""
LoL Chat Detox ayar ekranı: prompt düzenleme, kısayollar, model.
Kaydedilen ayarları çalışan detox ~2 saniye içinde otomatik alır.

Kullanım: python lol_settings.py  (ya da LoLDetoxSettings.exe)
"""
import ctypes

ctypes.windll.user32.SetProcessDPIAware()

import tkinter as tk
from tkinter import messagebox

import keyboard
import lol_config

BG = "#1e1e1e"
FG = "#e0e0e0"
BOX = "#2a2a2a"
ACCENT = "#3a7d44"


def main():
    cfg = lol_config.load_config()

    root = tk.Tk()
    root.title("LoL Chat Detox - Ayarlar")
    root.configure(bg=BG)
    root.geometry("720x640")

    def add_label(text, pady=(12, 2)):
        tk.Label(root, text=text, bg=BG, fg=FG, anchor="w",
                 font=("Segoe UI", 10, "bold")).pack(fill="x", padx=14, pady=pady)

    # --- prompt ---
    add_label("Prompt  ({msg} yazan yere oyuncunun mesajı gelir):", pady=(14, 2))
    prompt_box = tk.Text(root, height=16, wrap="word", bg=BOX, fg=FG,
                         insertbackground=FG, font=("Consolas", 9),
                         relief="flat", padx=8, pady=8)
    prompt_box.pack(fill="both", expand=True, padx=14)
    prompt_box.insert("1.0", cfg["prompt"])

    # --- alt satır: kısayollar + model ---
    row = tk.Frame(root, bg=BG)
    row.pack(fill="x", padx=14, pady=(12, 0))

    def add_entry(parent, label, value, width=16):
        col = tk.Frame(parent, bg=BG)
        col.pack(side="left", padx=(0, 18))
        tk.Label(col, text=label, bg=BG, fg=FG,
                 font=("Segoe UI", 9)).pack(anchor="w")
        e = tk.Entry(col, bg=BOX, fg=FG, insertbackground=FG,
                     relief="flat", width=width, font=("Consolas", 10))
        e.pack(ipady=4)
        e.insert(0, value)
        return e

    exit_entry = add_entry(row, "Çıkış kısayolu", cfg["exit_hotkey"])
    toggle_entry = add_entry(row, "Aç/Kapa kısayolu", cfg["toggle_hotkey"])
    model_entry = add_entry(row, "Gemini modeli", cfg["model"], width=26)

    status = tk.Label(root, text="", bg=BG, fg="#7fbf7f", font=("Segoe UI", 9))
    status.pack(fill="x", padx=14, pady=(8, 0))

    # --- kaydet / sıfırla ---
    def validate_hotkey(name, value):
        try:
            keyboard.parse_hotkey(value)
            return True
        except ValueError:
            messagebox.showerror("Hata", f"{name} geçersiz: '{value}'\n"
                                 "Örnek biçim: ctrl+alt+q")
            return False

    def save():
        prompt = prompt_box.get("1.0", "end").strip()
        if "{msg}" not in prompt:
            messagebox.showerror("Hata", "Prompt içinde {msg} olmalı — "
                                 "oyuncunun mesajı oraya yerleşiyor.")
            return
        exit_hk = exit_entry.get().strip().lower()
        toggle_hk = toggle_entry.get().strip().lower()
        if not validate_hotkey("Çıkış kısayolu", exit_hk):
            return
        if not validate_hotkey("Aç/Kapa kısayolu", toggle_hk):
            return
        if exit_hk == toggle_hk:
            messagebox.showerror("Hata", "İki kısayol aynı olamaz.")
            return
        model = model_entry.get().strip()
        if not model:
            messagebox.showerror("Hata", "Model adı boş olamaz.")
            return
        lol_config.save_config({"prompt": prompt, "model": model,
                                "exit_hotkey": exit_hk,
                                "toggle_hotkey": toggle_hk})
        status.config(text="✓ Kaydedildi — çalışan detox ~2 saniye içinde yeni ayarları alır")

    def reset():
        if not messagebox.askyesno("Sıfırla", "Tüm ayarlar varsayılana dönsün mü?"):
            return
        prompt_box.delete("1.0", "end")
        prompt_box.insert("1.0", lol_config.DEFAULTS["prompt"])
        for e, k in ((exit_entry, "exit_hotkey"), (toggle_entry, "toggle_hotkey"),
                     (model_entry, "model")):
            e.delete(0, "end")
            e.insert(0, lol_config.DEFAULTS[k])
        status.config(text="Varsayılanlar yüklendi — kaydetmeyi unutma")

    btns = tk.Frame(root, bg=BG)
    btns.pack(fill="x", padx=14, pady=12)
    tk.Button(btns, text="Kaydet", command=save, bg=ACCENT, fg="white",
              relief="flat", font=("Segoe UI", 10, "bold"),
              padx=24, pady=6).pack(side="left")
    tk.Button(btns, text="Varsayılanlara Dön", command=reset, bg=BOX, fg=FG,
              relief="flat", font=("Segoe UI", 10),
              padx=16, pady=6).pack(side="left", padx=10)

    root.mainloop()


if __name__ == "__main__":
    main()
