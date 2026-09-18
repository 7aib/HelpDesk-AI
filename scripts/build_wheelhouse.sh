#!/usr/bin/env bash
# Build a fully offline installation bundle for HelpDesk-AI.
#
# Run this ONCE on an internet-connected machine:
#     bash scripts/build_wheelhouse.sh
#
# Then copy the `wheelhouse/` directory (plus this repo) to the offline
# machine and install with:
#     python3 -m venv .venv && source .venv/bin/activate
#     pip install --no-index --find-links wheelhouse/ -r requirements/requirements.lock.txt
#
# Separate offline prerequisites (do these once on the target machine):
#   * Embedding model:  BAAI/bge-small-en-v1.5 pre-cached under
#     ~/.cache/huggingface/hub/ (the app forces offline mode, so it will
#     never try to download it). Alternatively set EMBEDDING_MODEL_DIR to a
#     local copy. See PYTHONPATH note below.
#   * Ollama LLM:       `ollama pull gemma4:12b` (or your chosen model) so
#     the chat model weights exist locally.
set -euo pipefail

cd "$(dirname "$0")/.."

echo ">>> Downloading pinned wheels into wheelhouse/ ..."
if [ -d wheelhouse ]; then
    read -r -p "wheelhouse/ already exists. Rebuild it? [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]] && rm -rf wheelhouse || exit 0
fi

python3 -m pip download \
    -r requirements/requirements.lock.txt \
    -d wheelhouse/

echo ">>> Done. wheelhouse/ has $(ls wheelhouse | wc -l) files."
echo
echo "To deploy offline, copy the repo + wheelhouse/ to the target machine and run:"
echo "  python3 -m venv .venv && source .venv/bin/activate"
echo "  pip install --no-index --find-links wheelhouse/ -r requirements/requirements.lock.txt"
echo "  python manage.py migrate"
echo "  python manage.py collectstatic --noinput"