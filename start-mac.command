#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

APP_PORT="${PORT:-7000}"
APP_URL="http://127.0.0.1:${APP_PORT}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Transparent Background Maker"
echo "App folder: $(pwd)"
echo

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3을 찾을 수 없습니다."
  echo "Mac에 Python 3.11 이상을 설치한 뒤 다시 실행하세요."
  echo "https://www.python.org/downloads/macos/"
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 이상이 필요합니다. 현재 버전: " + sys.version.split()[0])
PY

if [ ! -f "dist/index.html" ]; then
  echo "dist/index.html이 없습니다. Mac용 패키지 전체를 같은 폴더에 둔 뒤 실행하세요."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "가상환경을 생성합니다..."
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

echo "필요한 Python 패키지를 확인합니다..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdir -p models
export U2NET_HOME="$(pwd)/models"
export PORT="$APP_PORT"
export DEFAULT_PRESET="${DEFAULT_PRESET:-fast}"
export ENABLED_PRESETS="${ENABLED_PRESETS:-fast,best,balanced,pro}"
export FAST_MODEL="${FAST_MODEL:-isnet-general-use}"
export PUBLIC_ORIGINS="http://127.0.0.1:${APP_PORT},http://localhost:${APP_PORT}"

FAST_MARKER="models/.${FAST_MODEL}.ready"
if [ ! -f "$FAST_MARKER" ]; then
  echo
  echo "첫 실행 준비 중입니다. 기본 모델(${FAST_MODEL})을 내려받습니다."
  echo "인터넷 속도에 따라 몇 분 걸릴 수 있습니다."
  PREFETCH_MODELS_LIST="$FAST_MODEL" python scripts/prefetch_models.py
  touch "$FAST_MARKER"
fi

echo
echo "로컬 서버를 시작합니다: ${APP_URL}"
echo "종료하려면 이 터미널에서 Ctrl+C를 누르세요."

(sleep 2 && open "$APP_URL" >/dev/null 2>&1 || true) &
python -m uvicorn backend:app --host 127.0.0.1 --port "$APP_PORT"
