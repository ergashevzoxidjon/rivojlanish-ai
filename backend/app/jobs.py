"""Cron ishlari: yangiliklarni yig'ish va ertalabki yuborish."""
import logging
import traceback

from .bot import service
from .collector import collect_all, process_new_items, seed_sources
from .db import init_db, session_scope

log = logging.getLogger(__name__)


def collect_job(db) -> str:
    seed_sources(db)  # yangi standart manbalar qo'shilgan bo'lsa
    res = collect_all(db)
    made = process_new_items(db)
    errors = "; ".join(res["errors"]) or "yo'q"
    return f"{res['sources']} manba, {res['new_items']} yangi element, {len(made)} ta dars. Xatolar: {errors}"


def daily_job(db) -> str:
    return str(service.run_daily(db))


JOBS = {"collect": collect_job, "daily": daily_job}


def run_job(name: str) -> str:
    init_db()
    try:
        with session_scope() as db:
            msg = JOBS[name](db)
        if name != "daily":  # run_daily o'zi jurnalga yozadi
            with session_scope() as db:
                service.log_job(db, name, True, msg)
        return msg
    except Exception:
        err = traceback.format_exc()
        log.error(err)
        with session_scope() as db:
            service.log_job(db, name, False, err[-3000:])
        return err
