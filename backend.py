from __future__ import annotations

import asyncio
import io
import os
from pathlib import Path
from functools import lru_cache

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageFilter, ImageOps
from rembg import new_session, remove


MODEL_PRESETS = {
    "pro": {
        "model": "bria-rmbg + birefnet-general-lite",
        "models": ("bria-rmbg", "birefnet-general-lite"),
        "label": "Stable Ensemble Pro",
        "description": "memory-safe two-model alpha-mask ensemble with edge color cleanup",
    },
    "best": {
        "model": "bria-rmbg",
        "models": ("bria-rmbg",),
        "label": "BRIA RMBG",
        "description": "state-of-the-art background removal model",
    },
    "balanced": {
        "model": "birefnet-general-lite",
        "models": ("birefnet-general-lite",),
        "label": "BiRefNet General Lite",
        "description": "lighter general-purpose salient object model",
    },
    "fast": {
        "model": "isnet-general-use",
        "models": ("isnet-general-use",),
        "label": "IS-Net General",
        "description": "good general-purpose model with lighter runtime",
    },
}

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "12")) * 1024 * 1024
MAX_IMAGE_MEGAPIXELS = float(os.getenv("MAX_IMAGE_MEGAPIXELS", "12"))
INFERENCE_CONCURRENCY = int(os.getenv("INFERENCE_CONCURRENCY", "1"))
DEPLOYMENT_PROFILE = os.getenv("DEPLOYMENT_PROFILE", "standard").strip().lower()

requested_default_preset = os.getenv(
    "DEFAULT_PRESET",
    "fast" if DEPLOYMENT_PROFILE == "free" else "pro",
).strip()
DEFAULT_PRESET = requested_default_preset if requested_default_preset in MODEL_PRESETS else "fast"

enabled_preset_names = [
    preset.strip()
    for preset in os.getenv(
        "ENABLED_PRESETS",
        DEFAULT_PRESET if DEPLOYMENT_PROFILE == "free" else ",".join(MODEL_PRESETS.keys()),
    ).split(",")
    if preset.strip() in MODEL_PRESETS
]

if not enabled_preset_names:
    enabled_preset_names = [DEFAULT_PRESET]

AVAILABLE_MODEL_PRESETS = {preset: MODEL_PRESETS[preset] for preset in enabled_preset_names}

if DEFAULT_PRESET not in AVAILABLE_MODEL_PRESETS:
    DEFAULT_PRESET = next(iter(AVAILABLE_MODEL_PRESETS))

app = FastAPI(title="Transparent Background Maker", version="0.3.0")
inference_semaphore = asyncio.Semaphore(max(1, INFERENCE_CONCURRENCY))

configured_origins = [origin.strip() for origin in os.getenv("PUBLIC_ORIGINS", "").split(",") if origin.strip()]
cors_origins = configured_origins or [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache(maxsize=8)
def get_session(model_name: str):
    return new_session(model_name)


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def validate_image_size(image_bytes: bytes) -> None:
    with Image.open(io.BytesIO(image_bytes)) as image:
        megapixels = (image.width * image.height) / 1_000_000

    if megapixels > MAX_IMAGE_MEGAPIXELS:
        raise HTTPException(
            status_code=413,
            detail=f"이미지가 너무 큽니다. 최대 {MAX_IMAGE_MEGAPIXELS:g}MP까지 처리할 수 있습니다.",
        )


def refine_alpha_channel(alpha: Image.Image, edge_smooth: int, erode: int) -> Image.Image:
    edge_smooth = clamp(edge_smooth, 0, 5)
    erode = clamp(erode, 0, 3)

    refined = alpha.convert("L")

    if erode:
        refined = refined.filter(ImageFilter.MinFilter(erode * 2 + 1))

    if edge_smooth:
        refined = refined.filter(ImageFilter.GaussianBlur(radius=edge_smooth))

    return refined


def encode_png(rgb: Image.Image, alpha: Image.Image) -> bytes:
    alpha_l = alpha.convert("L")
    rgb_array = np.asarray(rgb.convert("RGB"), dtype=np.uint8).copy()
    alpha_array = np.asarray(alpha_l, dtype=np.uint8)

    # Fully transparent pixels should not keep the original background RGB.
    # Some viewers ignore alpha, and hidden RGB also worsens compression.
    rgb_array[alpha_array <= 2] = 0

    clean_rgb = Image.fromarray(rgb_array, mode="RGB")
    rgba = Image.merge("RGBA", (*clean_rgb.split(), alpha_l))
    buffer = io.BytesIO()
    rgba.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def final_from_rembg_output(
    image_bytes: bytes,
    output_bytes: bytes,
    edge_smooth: int,
    erode: int,
    decontaminate: bool,
) -> bytes:
    with Image.open(io.BytesIO(output_bytes)) as output_image:
        output_rgba = output_image.convert("RGBA")
        red, green, blue, alpha = output_rgba.split()
        alpha = refine_alpha_channel(alpha, edge_smooth=edge_smooth, erode=erode)
        rgb = Image.merge("RGB", (red, green, blue))

    if decontaminate:
        with Image.open(io.BytesIO(image_bytes)) as original_image:
            rgb = decontaminate_edges(original_image.convert("RGB"), alpha)

    return encode_png(rgb, alpha)


def mask_from_model(
    image_bytes: bytes,
    model_name: str,
    size: tuple[int, int],
    alpha_matting: bool,
) -> Image.Image:
    session = get_session(model_name)
    output = remove(
        image_bytes,
        session=session,
        force_return_bytes=True,
        only_mask=True,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
        post_process_mask=True,
    )

    if not isinstance(output, bytes):
        raise RuntimeError("Unexpected rembg mask output type")

    with Image.open(io.BytesIO(output)) as mask:
        return ImageOps.grayscale(mask).resize(size)


def combine_masks(masks: list[Image.Image]) -> Image.Image:
    if len(masks) == 1:
        return masks[0].convert("L")

    arrays = [np.asarray(mask.convert("L"), dtype=np.float32) for mask in masks]
    combined = (arrays[0] * 0.7) + (arrays[1] * 0.3)
    detail = np.maximum.reduce(arrays)

    # Keep fine foreground that at least one model sees, without letting a single noisy
    # mask dominate the whole result.
    combined = np.where(
        (detail > combined) & (combined > 18),
        (combined * 0.85) + (detail * 0.15),
        combined,
    )
    return Image.fromarray(np.clip(combined, 0, 255).astype(np.uint8), mode="L")


def decontaminate_edges(rgb: Image.Image, alpha: Image.Image) -> Image.Image:
    rgb_array = np.asarray(rgb.convert("RGB"), dtype=np.float32)
    alpha_array = np.asarray(alpha.convert("L"), dtype=np.float32) / 255.0

    background_pixels = rgb_array[alpha_array < 0.03]

    if background_pixels.size:
        background = np.median(background_pixels, axis=0)
    else:
        corners = np.concatenate(
            [
                rgb_array[:10, :10].reshape(-1, 3),
                rgb_array[:10, -10:].reshape(-1, 3),
                rgb_array[-10:, :10].reshape(-1, 3),
                rgb_array[-10:, -10:].reshape(-1, 3),
            ],
            axis=0,
        )
        background = np.median(corners, axis=0)

    edge_mask = (alpha_array > 0.04) & (alpha_array < 0.98)
    safe_alpha = np.maximum(alpha_array[..., None], 0.08)
    corrected = (rgb_array - ((1.0 - safe_alpha) * background)) / safe_alpha
    corrected = np.clip(corrected, 0, 255)

    strength = np.clip((0.98 - alpha_array) / 0.94, 0, 1)[..., None] * 0.68
    cleaned = np.where(edge_mask[..., None], (rgb_array * (1 - strength)) + (corrected * strength), rgb_array)

    return Image.fromarray(np.clip(cleaned, 0, 255).astype(np.uint8), mode="RGB")


def remove_background_pro_sync(
    image_bytes: bytes,
    alpha_matting: bool,
    edge_smooth: int,
    erode: int,
) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as original_image:
        original_rgb = original_image.convert("RGB")
        size = original_rgb.size

    masks = []
    failures = []

    for model_name in MODEL_PRESETS["pro"]["models"]:
        try:
            masks.append(mask_from_model(image_bytes, model_name, size, alpha_matting=alpha_matting))
        except Exception as exc:
            failures.append(f"{model_name}: {exc}")

    if not masks:
        raise RuntimeError("; ".join(failures) or "all pro models failed")

    alpha = combine_masks(masks)
    alpha = refine_alpha_channel(alpha, edge_smooth=edge_smooth, erode=erode)
    rgb = decontaminate_edges(original_rgb, alpha)

    return encode_png(rgb, alpha)


def remove_background_sync(
    image_bytes: bytes,
    preset: str,
    alpha_matting: bool,
    edge_smooth: int,
    erode: int,
) -> bytes:
    if preset == "pro":
        return remove_background_pro_sync(
            image_bytes,
            alpha_matting=alpha_matting,
            edge_smooth=edge_smooth,
            erode=erode,
        )

    model_name = MODEL_PRESETS[preset]["model"]
    session = get_session(model_name)
    output = remove(
        image_bytes,
        session=session,
        force_return_bytes=True,
        alpha_matting=alpha_matting,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
        post_process_mask=True,
    )

    if not isinstance(output, bytes):
        raise RuntimeError("Unexpected rembg output type")

    return final_from_rembg_output(
        image_bytes,
        output,
        edge_smooth=edge_smooth,
        erode=erode,
        decontaminate=preset == "best",
    )


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "engine": "rembg",
        "deploymentProfile": DEPLOYMENT_PROFILE,
        "defaultPreset": DEFAULT_PRESET,
        "presets": AVAILABLE_MODEL_PRESETS,
        "limits": {
            "maxUploadMb": MAX_UPLOAD_BYTES // 1024 // 1024,
            "maxImageMegapixels": MAX_IMAGE_MEGAPIXELS,
            "inferenceConcurrency": max(1, INFERENCE_CONCURRENCY),
        },
    }


@app.post("/api/remove-background")
async def remove_background(
    file: UploadFile = File(...),
    preset: str = Form(DEFAULT_PRESET),
    alpha_matting: bool = Form(True),
    edge_smooth: int = Form(3),
    erode: int = Form(1),
):
    if preset not in AVAILABLE_MODEL_PRESETS:
        raise HTTPException(status_code=400, detail="Unknown model preset")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="PNG, JPG, WEBP 이미지만 처리할 수 있습니다.")

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="이미지 파일이 비어 있습니다.")

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"파일이 너무 큽니다. 최대 {MAX_UPLOAD_BYTES // 1024 // 1024}MB까지 업로드할 수 있습니다.",
        )

    validate_image_size(image_bytes)
    edge_smooth = clamp(edge_smooth, 0, 5)
    erode = clamp(erode, 0, 3)

    try:
        async with inference_semaphore:
            output = await asyncio.to_thread(
                remove_background_sync,
                image_bytes,
                preset,
                alpha_matting,
                edge_smooth,
                erode,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"배경 제거 실패: {exc}") from exc

    return Response(
        content=output,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "X-Background-Removal-Engine": "rembg",
            "X-Background-Removal-Model": MODEL_PRESETS[preset]["model"],
            "X-Alpha-Matting": str(alpha_matting).lower(),
            "X-Edge-Smooth": str(edge_smooth),
            "X-Erode": str(erode),
        },
    )


if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/")
def serve_index():
    index_path = DIST_DIR / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build first.")

    return FileResponse(index_path)


@app.get("/{full_path:path}")
def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")

    requested_path = DIST_DIR / full_path

    if requested_path.is_file():
        return FileResponse(requested_path)

    return serve_index()
