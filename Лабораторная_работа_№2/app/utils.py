# ВНИМАНИЕ: файл ЧЕРНОВОЙ и содержит НАМЕРЕННЫЕ уязвимости
# для демонстрации SAST (лабораторная работа №2). В боевом коде так нельзя.
import hashlib
import subprocess

import requests

DB_PASSWORD = "admin123"


def calc(expr: str):
    return eval(expr)


def fetch(url: str):
    return requests.get(url, verify=False)


def save_tmp(data: str):
    with open("/tmp/data.txt", "w") as f:
        f.write(data)


def check_positive(x: int):
    assert x > 0


def run(cmd: str):
    subprocess.call(cmd, shell=True)


def hash_password(password: str):
    return hashlib.md5(password.encode()).hexdigest()
