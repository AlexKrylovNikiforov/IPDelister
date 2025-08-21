#!/usr/bin/env zsh
set -euo pipefail

# ===== ПАРАМЕТРЫ СБОРКИ =====
APP_NAME="IPDelister"        # имя исполняемого файла
ENTRY="main.py"              # точка входа
DMG_NAME="${APP_NAME}-macOS.dmg"
VENV=".venv_build"           # изолированное окружение для сборки
PYTHON_BIN="${PYTHON_BIN:-python3}"  # можно переопределить переменной окружения
# ============================

echo "▶️  Создаю virtualenv..."
$PYTHON_BIN -m venv "$VENV"
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel

echo "▶️  Ставлю зависимости проекта..."
pip install -r requirements.txt

echo "▶️  Ставлю инструменты сборки..."
pip install pyinstaller

echo "▶️  Чищу прошлые сборки..."
rm -rf build dist "${APP_NAME}.spec" .dmg-stage || true

echo "▶️  Сборка onefile бинаря через PyInstaller..."
pyinstaller "$ENTRY" \
  --name "$APP_NAME" \
  --onefile \
  --noconfirm \
  --clean

BIN_PATH="dist/${APP_NAME}"
[[ -f "$BIN_PATH" ]] || { echo "❌ Не найден бинарь $BIN_PATH"; exit 1; }
echo "✅ Собрано: $BIN_PATH"

echo "▶️  Готовлю содержимое для DMG..."
STAGE=".dmg-stage"
mkdir -p "$STAGE"
cp "$BIN_PATH" "$STAGE/"

# Добавим пример входного файла (если есть)
[[ -f "ip.txt" ]] && cp "ip.txt" "$STAGE/ip.example.txt"

# Добавим README (если есть)
[[ -f "README.md" ]] && cp "README.md" "$STAGE/README.md"

# Создаём ярлык для двойного клика (запустит в Terminal)
cat > "$STAGE/Run ${APP_NAME}.command" <<'EOF'
#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
# Запускаем бинарь (интерактив по умолчанию, браузер — Chrome)
"$DIR/IPDelister"
echo
read -n 1 -s -r -p "Press any key to close..."
EOF
chmod +x "$STAGE/Run ${APP_NAME}.command"

echo "▶️  Собираю DMG..."
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG_NAME"

echo "🧹 Убираю временные файлы..."
rm -rf "$STAGE"

echo "✅ Готово: $DMG_NAME"
echo "   Внутри:"
echo "     • ${APP_NAME}                (исполняемый файл)"
echo "     • Run ${APP_NAME}.command    (ярлык для двойного клика)"
echo "     • ip.example.txt             (если был ip.txt)"
echo "     • README.md                  (если был)"
