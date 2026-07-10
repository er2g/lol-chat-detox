# -*- coding: utf-8 -*-
"""Geriye uyumluluk: ayarlar artık tek uygulamada. lol_app.py açılır."""
import runpy
import os

if __name__ == "__main__":
    runpy.run_path(os.path.join(os.path.dirname(__file__), "lol_app.py"),
                   run_name="__main__")
