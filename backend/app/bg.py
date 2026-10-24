"""Fon ishlari (AI javobi, dars yozish, webhook) uchun yagona nuqta — testlarda almashtiriladi."""
import threading


def run_bg(target, *args) -> None:
    threading.Thread(target=target, args=args, daemon=True).start()
