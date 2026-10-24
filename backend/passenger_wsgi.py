"""cPanel "Setup Python App" (Passenger) uchun kirish nuqtasi.

Application startup file: passenger_wsgi.py
Application Entry point:  application
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)  # .env va sqlite fayli shu papkadan o'qiladi

from a2wsgi import ASGIMiddleware  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app, check_config  # noqa: E402

# a2wsgi lifespan hodisalarini ishga tushirmaydi — shuning uchun bu yerda bajaramiz
check_config()
init_db()

application = ASGIMiddleware(app)
