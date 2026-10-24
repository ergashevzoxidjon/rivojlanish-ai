"""Yangiliklarni yig'ib, AI bilan darsga aylantiradi. Cron: har 3 soatda.
   0 */3 * * *  cd ~/rivojlanish-ai/backend && ~/virtualenv/.../bin/python scripts/cron_collect.py
"""
import _bootstrap  # noqa: F401

from app.jobs import run_job

print(run_job("collect"))
