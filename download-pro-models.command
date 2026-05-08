#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

mkdir -p models
export U2NET_HOME="$(pwd)/models"

echo "고품질/프로 모델을 미리 내려받습니다."
echo "용량이 크고 시간이 오래 걸릴 수 있습니다."
PREFETCH_MODELS_LIST="isnet-general-use,bria-rmbg,birefnet-general-lite" python scripts/prefetch_models.py
touch models/.isnet-general-use.ready
touch models/.bria-rmbg.ready
touch models/.birefnet-general-lite.ready

echo "완료되었습니다. 이제 start-mac.command를 실행하면 됩니다."
