import ast
import hashlib
import operator
import os
import subprocess
import tempfile

import requests

# Пароль берём из переменной окружения, а не из кода
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def _eval_node(node):
    """Вычисляет только арифметические выражения, без вызова функций и имён."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    raise ValueError("Unsupported expression")


def calc(expr: str):
    # Вместо eval: разбираем строку в дерево и считаем только разрешённые операции
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body)


def fetch(url: str):
    # verify=True по умолчанию, timeout защищает от зависания
    return requests.get(url, timeout=5)


def save_tmp(data: str):
    # Временный файл со случайным именем вместо предсказуемого /tmp/data.txt
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        f.write(data)
        return f.name


def check_positive(x: int):
    # Проверка работает всегда, даже при запуске с python -O (в отличие от assert)
    if x <= 0:
        raise ValueError("x must be positive")


def run(args: list[str]):
    # Список аргументов вместо строки и без shell=True
    return subprocess.run(args, check=True)


def hash_password(password: str):
    # scrypt вместо MD5: медленный, с солью, подходит для паролей
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + digest.hex()
