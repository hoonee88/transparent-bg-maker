from __future__ import annotations

import os

from rembg import new_session


DEFAULT_MODELS = (
    "bria-rmbg",
    "birefnet-general-lite",
    "isnet-general-use",
)


def selected_models() -> list[str]:
    configured_models = os.getenv("PREFETCH_MODELS_LIST", "").strip()

    if not configured_models:
        return list(DEFAULT_MODELS)

    return [model.strip() for model in configured_models.split(",") if model.strip()]


def main() -> None:
    for model in selected_models():
        print(f"Prefetching {model}...")
        new_session(model)
    print("Model prefetch complete.")


if __name__ == "__main__":
    main()
