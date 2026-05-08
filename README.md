# Transparent Background Maker

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/hoonee88/transparent-bg-maker)

AI 배경 제거 웹앱입니다. 이미지를 업로드하면 로컬/서버에서 배경을 제거하고 투명 PNG로 내려받을 수 있습니다.

## 배포

가장 쉬운 방법은 위의 **Deploy to Render** 버튼을 누르는 것입니다. Render가 이 저장소의 `render.yaml`을 읽어서 Docker 웹서비스를 생성합니다.

기본 배포 설정:

- Runtime: Docker
- Region: Singapore
- Plan: Standard
- Health check: `/api/health`
- Auto deploy: GitHub CI 통과 후 배포

무료/저사양 인스턴스는 AI 모델 메모리 때문에 실패할 수 있습니다. 비용을 줄여 테스트만 할 때는 `render.yaml`의 `plan`을 `starter` 또는 `free`로 낮춰볼 수 있지만, 공개 서비스용으로는 `standard` 이상을 권장합니다.

## 로컬 실행

```powershell
npm install
npm run build
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn backend:app --host 0.0.0.0 --port 7000
```

브라우저에서 `http://127.0.0.1:7000`을 열면 됩니다.
