#!/usr/bin/env bash
set -euo pipefail

APP_NAME="IPDelister"
ENTRY="main.py"
VENV=".venv_build"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "▶️  Создаю virtualenv..."
$PYTHON_BIN -m venv "$VENV"
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel

echo "▶️  Ставлю зависимости проекта..."
pip install -r requirements.txt
pip install pyinstaller

echo "▶️  Чищу прошлые сборки..."
rm -rf build dist "${APP_NAME}.spec" || true

echo "▶️  Сборка onefile бинаря..."
pyinstaller "$ENTRY" \
  --name "$APP_NAME" \
  --onefile \
  --noconfirm \
  --clean

BIN_PATH="dist/${APP_NAME}"
[[ -f "$BIN_PATH" ]] || { echo "❌ Не найден бинарь $BIN_PATH"; exit 1; }

echo "✅ Собрано: $BIN_PATH"
echo "▶️  Запусти ./dist/${APP_NAME}, чтобы проверить работу"
