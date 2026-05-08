import './styles.css';

type AppState = 'empty' | 'ready' | 'processing' | 'done' | 'error';
type QualityMode = 'pro' | 'best' | 'balanced' | 'fast';

const apiBaseUrl = import.meta.env.DEV ? 'http://127.0.0.1:7000/api' : '/api';

const qualityModes: Record<QualityMode, { label: string; model: string; note: string }> = {
  pro: {
    label: '프로',
    model: 'BRIA + BiRefNet Lite',
    note: '안정형 앙상블과 경계 색 보정 사용',
  },
  best: {
    label: '최고품질',
    model: 'bria-rmbg',
    note: 'BRIA RMBG 모델 사용',
  },
  balanced: {
    label: '균형',
    model: 'birefnet-general-lite',
    note: 'BiRefNet General Lite 모델 사용',
  },
  fast: {
    label: '빠름',
    model: 'isnet-general-use',
    note: 'IS-Net General 모델 사용',
  },
};

const app = document.querySelector<HTMLDivElement>('#app');

if (!app) {
  throw new Error('App root not found');
}

app.innerHTML = `
  <main class="app-shell">
    <section class="workspace" aria-label="배경 제거 작업 영역">
      <header class="topbar">
        <div>
          <p class="eyebrow">Local AI Cutout</p>
          <h1>투명 배경 메이커</h1>
        </div>
        <div class="status-pill" id="statusPill">준비됨</div>
      </header>

      <div class="tool-grid">
        <aside class="side-panel">
          <label class="dropzone" id="dropzone" for="fileInput">
            <input id="fileInput" type="file" accept="image/png,image/jpeg,image/webp" />
            <span class="drop-icon" aria-hidden="true"></span>
            <span class="drop-title">이미지 선택</span>
            <span class="drop-meta">PNG · JPG · WEBP</span>
          </label>

          <fieldset class="quality-card" id="qualityCard">
            <legend>처리 품질</legend>
            <label class="quality-option">
              <input type="radio" name="qualityMode" value="pro" checked />
              <span>
                <strong>프로</strong>
                <small>BRIA + BiRefNet Lite</small>
              </span>
            </label>
            <label class="quality-option">
              <input type="radio" name="qualityMode" value="best" />
              <span>
                <strong>최고품질</strong>
                <small>BRIA RMBG 모델</small>
              </span>
            </label>
            <label class="quality-option">
              <input type="radio" name="qualityMode" value="balanced" />
              <span>
                <strong>균형</strong>
                <small>BiRefNet General Lite</small>
              </span>
            </label>
            <label class="quality-option">
              <input type="radio" name="qualityMode" value="fast" />
              <span>
                <strong>빠름</strong>
                <small>IS-Net General 모델</small>
              </span>
            </label>
          </fieldset>

          <fieldset class="refine-card">
            <legend>가장자리 정제</legend>
            <label class="slider-row" for="edgeSmoothInput">
              <span>
                <strong>부드럽게</strong>
                <small>마스크 가장자리 블러</small>
              </span>
              <output id="edgeSmoothValue">3</output>
            </label>
            <input class="slider" id="edgeSmoothInput" type="range" min="0" max="5" step="1" value="3" />

            <label class="slider-row" for="erodeInput">
              <span>
                <strong>테두리 제거</strong>
                <small>배경색 번짐 줄이기</small>
              </span>
              <output id="erodeValue">1</output>
            </label>
            <input class="slider" id="erodeInput" type="range" min="0" max="3" step="1" value="1" />

            <label class="toggle-row">
              <input id="alphaMattingInput" type="checkbox" checked />
              <span>
                <strong>알파 매팅</strong>
                <small>머리카락과 얇은 경계 보정</small>
              </span>
            </label>
          </fieldset>

          <div class="actions">
            <button class="primary" id="removeButton" type="button" disabled>배경 제거</button>
            <button class="secondary" id="downloadButton" type="button" disabled>PNG 저장</button>
            <button class="ghost" id="resetButton" type="button" disabled>초기화</button>
          </div>

          <div class="progress-wrap" aria-live="polite">
            <div class="progress-track">
              <div class="progress-bar" id="progressBar"></div>
            </div>
            <p id="message">이미지를 선택하면 미리보기가 표시됩니다.</p>
          </div>
        </aside>

        <section class="preview-panel">
          <div class="preview-toolbar">
            <div class="segmented" role="tablist" aria-label="미리보기 모드">
              <button class="segment is-active" id="originalTab" type="button">원본</button>
              <button class="segment" id="resultTab" type="button" disabled>결과</button>
            </div>
            <span id="fileInfo">선택된 파일 없음</span>
          </div>

          <div class="preview-board checkerboard" id="previewBoard">
            <div class="empty-state" id="emptyState">
              <span class="empty-mark" aria-hidden="true"></span>
            </div>
            <img id="previewImage" alt="선택한 이미지 미리보기" hidden />
          </div>
        </section>
      </div>
    </section>
  </main>
`;

const fileInput = document.querySelector<HTMLInputElement>('#fileInput')!;
const dropzone = document.querySelector<HTMLLabelElement>('#dropzone')!;
const removeButton = document.querySelector<HTMLButtonElement>('#removeButton')!;
const downloadButton = document.querySelector<HTMLButtonElement>('#downloadButton')!;
const resetButton = document.querySelector<HTMLButtonElement>('#resetButton')!;
const originalTab = document.querySelector<HTMLButtonElement>('#originalTab')!;
const resultTab = document.querySelector<HTMLButtonElement>('#resultTab')!;
const previewImage = document.querySelector<HTMLImageElement>('#previewImage')!;
const emptyState = document.querySelector<HTMLDivElement>('#emptyState')!;
const statusPill = document.querySelector<HTMLDivElement>('#statusPill')!;
const progressBar = document.querySelector<HTMLDivElement>('#progressBar')!;
const message = document.querySelector<HTMLParagraphElement>('#message')!;
const fileInfo = document.querySelector<HTMLSpanElement>('#fileInfo')!;
const qualityInputs = Array.from(document.querySelectorAll<HTMLInputElement>('input[name="qualityMode"]'));
const edgeSmoothInput = document.querySelector<HTMLInputElement>('#edgeSmoothInput')!;
const edgeSmoothValue = document.querySelector<HTMLOutputElement>('#edgeSmoothValue')!;
const erodeInput = document.querySelector<HTMLInputElement>('#erodeInput')!;
const erodeValue = document.querySelector<HTMLOutputElement>('#erodeValue')!;
const alphaMattingInput = document.querySelector<HTMLInputElement>('#alphaMattingInput')!;
const refineInputs = [edgeSmoothInput, erodeInput, alphaMattingInput];

let currentFile: File | null = null;
let originalUrl: string | null = null;
let resultUrl: string | null = null;
let resultBlob: Blob | null = null;
let visibleImage: 'original' | 'result' = 'original';
let selectedQuality: QualityMode = 'pro';

const setState = (state: AppState, text: string) => {
  document.body.dataset.state = state;
  statusPill.textContent = text;
  removeButton.disabled = !currentFile || state === 'processing';
  downloadButton.disabled = !resultBlob || state === 'processing';
  resetButton.disabled = !currentFile && !resultBlob;
  resultTab.disabled = !resultUrl;
  fileInput.disabled = state === 'processing';
  qualityInputs.forEach((input) => {
    input.disabled = state === 'processing';
  });
  refineInputs.forEach((input) => {
    input.disabled = state === 'processing';
  });
};

const setProgress = (percent: number) => {
  progressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
};

const revoke = (url: string | null) => {
  if (url) URL.revokeObjectURL(url);
};

const renderPreview = () => {
  const nextUrl = visibleImage === 'result' ? resultUrl : originalUrl;
  previewImage.hidden = !nextUrl;
  emptyState.hidden = Boolean(nextUrl);

  if (nextUrl) {
    previewImage.src = nextUrl;
  } else {
    previewImage.removeAttribute('src');
  }

  originalTab.classList.toggle('is-active', visibleImage === 'original');
  resultTab.classList.toggle('is-active', visibleImage === 'result');
};

const resetResult = () => {
  revoke(resultUrl);
  resultUrl = null;
  resultBlob = null;
  visibleImage = 'original';
  setProgress(0);
};

const formatSize = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

const updateRefineLabels = () => {
  edgeSmoothValue.value = edgeSmoothInput.value;
  erodeValue.value = erodeInput.value;
};

const describeRefinement = () => {
  const matting = alphaMattingInput.checked ? '알파 매팅 켬' : '알파 매팅 끔';
  return `부드럽게 ${edgeSmoothInput.value}, 테두리 제거 ${erodeInput.value}, ${matting}`;
};

const handleFile = (file: File) => {
  if (!file.type.startsWith('image/')) {
    setState('error', '오류');
    message.textContent = '이미지 파일만 선택할 수 있습니다.';
    return;
  }

  resetResult();
  revoke(originalUrl);
  currentFile = file;
  originalUrl = URL.createObjectURL(file);
  visibleImage = 'original';
  fileInfo.textContent = `${file.name} · ${formatSize(file.size)}`;
  message.textContent = '준비되었습니다.';
  setState('ready', '대기 중');
  renderPreview();
};

const removeSelectedBackground = async () => {
  if (!currentFile) return;

  resetResult();
  const quality = qualityModes[selectedQuality];
  setState('processing', '처리 중');
  message.textContent = `${quality.label} 모델(${quality.model})을 준비하고 있습니다. 첫 실행은 모델 다운로드 때문에 오래 걸릴 수 있습니다.`;
  setProgress(5);

  try {
    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('preset', selectedQuality);
    formData.append('edge_smooth', edgeSmoothInput.value);
    formData.append('erode', erodeInput.value);
    formData.append('alpha_matting', String(alphaMattingInput.checked));
    setProgress(28);

    const response = await fetch(`${apiBaseUrl}/remove-background`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? `서버 오류 ${response.status}`);
    }

    setProgress(86);
    resultBlob = await response.blob();
    resultUrl = URL.createObjectURL(resultBlob);
    visibleImage = 'result';
    setProgress(100);
    message.textContent = `${quality.label} 모드(${quality.model})로 완료되었습니다. ${describeRefinement()}.`;
    setState('done', '완료');
    renderPreview();
  } catch (error) {
    console.error(error);
    setProgress(0);
    message.textContent = error instanceof Error ? error.message : '처리 중 문제가 발생했습니다.';
    setState('error', '오류');
  }
};

const downloadResult = () => {
  if (!resultBlob || !currentFile) return;

  const sourceName = currentFile.name.replace(/\.[^.]+$/, '');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(resultBlob);
  link.download = `${sourceName}-transparent.png`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
};

const resetAll = () => {
  revoke(originalUrl);
  resetResult();
  currentFile = null;
  originalUrl = null;
  fileInput.value = '';
  fileInfo.textContent = '선택된 파일 없음';
  message.textContent = '이미지를 선택하면 미리보기가 표시됩니다.';
  setState('empty', '준비됨');
  renderPreview();
};

fileInput.addEventListener('change', () => {
  const file = fileInput.files?.[0];
  if (file) handleFile(file);
});

dropzone.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropzone.classList.add('is-dragging');
});

dropzone.addEventListener('dragleave', () => {
  dropzone.classList.remove('is-dragging');
});

dropzone.addEventListener('drop', (event) => {
  event.preventDefault();
  dropzone.classList.remove('is-dragging');
  const file = event.dataTransfer?.files[0];
  if (file) handleFile(file);
});

document.addEventListener('paste', (event) => {
  const file = Array.from(event.clipboardData?.files ?? []).find((item) => item.type.startsWith('image/'));
  if (file) handleFile(file);
});

removeButton.addEventListener('click', removeSelectedBackground);
downloadButton.addEventListener('click', downloadResult);
resetButton.addEventListener('click', resetAll);
qualityInputs.forEach((input) => {
  input.addEventListener('change', () => {
    if (!input.checked) return;
    selectedQuality = input.value as QualityMode;
    resetResult();
    renderPreview();
    message.textContent = `${qualityModes[selectedQuality].label} 모드가 선택되었습니다. ${qualityModes[selectedQuality].note}.`;
    setState(currentFile ? 'ready' : 'empty', currentFile ? '대기 중' : '준비됨');
  });
});
refineInputs.forEach((input) => {
  input.addEventListener('input', () => {
    updateRefineLabels();
    if (!currentFile) return;
    resetResult();
    renderPreview();
    message.textContent = `가장자리 정제가 변경되었습니다. ${describeRefinement()}.`;
    setState('ready', '대기 중');
  });
});

originalTab.addEventListener('click', () => {
  visibleImage = 'original';
  renderPreview();
});

resultTab.addEventListener('click', () => {
  if (!resultUrl) return;
  visibleImage = 'result';
  renderPreview();
});

setState('empty', '준비됨');
updateRefineLabels();
