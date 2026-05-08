from __future__ import annotations

from rembg import new_session


MODELS = (
    "bria-rmbg",
    "birefnet-general-lite",
    "isnet-general-use",
)


def main() -> None:
    for model in MODELS:
        print(f"Prefetching {model}...")
        new_session(model)
    print("Model prefetch complete.")


if __name__ == "__main__":
    main()
