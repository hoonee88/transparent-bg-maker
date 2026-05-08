# Transparent Background Maker

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/hoonee88/transparent-bg-maker)

AI 배경 제거 웹앱입니다. 이미지를 업로드하면 로컬/서버에서 배경을 제거하고 투명 PNG로 내려받을 수 있습니다.

## 배포

가장 쉬운 방법은 위의 **Deploy to Render** 버튼을 누르는 것입니다. Render가 이 저장소의 `render.yaml`을 읽어서 Docker 웹서비스를 생성합니다.

기본 배포 설정:

- Runtime: Docker
- Region: Singapore
- Plan: Free
- Health check: `/api/health`
- Auto deploy: GitHub CI 통과 후 배포

무료 인스턴스에서는 메모리 보호를 위해 `fast` 모델만 활성화합니다. 공개 서비스로 안정적으로 운영하려면 `render.yaml`의 `plan`을 `standard` 이상으로 올리고 `ENABLED_PRESETS` 값을 `pro,best,balanced,fast`처럼 확장하는 것을 권장합니다.

## 로컬 실행

```powershell
npm install
npm run build
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn backend:app --host 0.0.0.0 --port 7000
```

브라우저에서 `http://127.0.0.1:7000`을 열면 됩니다.
