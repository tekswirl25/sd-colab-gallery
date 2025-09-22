#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo "❌ Error at line $LINENO"; exit 1' ERR

KEEP=${KEEP:-5}
HASH="${1:-HEAD}"

# убедимся, что мы в git-репо и возьмём корень
repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "❌ Not a git repository"; exit 1; }
cd "$repo_root"

# проверим валидность коммита/ссылки
if ! git rev-parse --verify "${HASH}^{commit}" >/dev/null 2>&1; then
  echo "❌ Invalid commit ref: $HASH"
  exit 1
fi

SHORT_HASH="$(git rev-parse --short "$HASH")"
ARCHIVE_DIR="$repo_root/archives"
ARCHIVE_FILE="$ARCHIVE_DIR/commit_${SHORT_HASH}.zip"

mkdir -p "$ARCHIVE_DIR"

# включаем только исходники/конфиги
INCLUDE_REGEX='\.(py|ipynb|json|ya?ml|md)$'
FILES="$(git ls-tree -r --name-only "$HASH" | grep -E "$INCLUDE_REGEX" || true)"

# применим исключения из .archiveignore (regex-паттерны)
if [[ -f "$repo_root/.archiveignore" ]]; then
  while IFS= read -r pattern; do
    [[ -z "$pattern" || "$pattern" =~ ^[[:space:]]*# ]] && continue
    FILES="$(echo "$FILES" | grep -v -E "$pattern" || true)"
  done < "$repo_root/.archiveignore"
fi

if [[ -z "${FILES//[$'\t\r\n ']/}" ]]; then
  echo "ℹ️  No matching files to archive after filters."
  exit 0
fi

# упаковка (zip → 7z; иначе сообщить)
if command -v zip >/dev/null 2>&1; then
  # передаём список файлов через stdin, чтобы не словить проблемы с пробелами
  echo "$FILES" | zip -q -@ "$ARCHIVE_FILE"
elif command -v 7z >/dev/null 2>&1; then
  tmpfile="$(mktemp)"
  echo "$FILES" > "$tmpfile"
  7z a -tzip "$ARCHIVE_FILE" @"$tmpfile" >/dev/null
  rm -f "$tmpfile"
else
  echo "❌ No archiver found (zip or 7z). macOS: zip есть по умолчанию; Linux: sudo apt-get install zip"
  exit 1
fi

SIZE="$(du -h "$ARCHIVE_FILE" | awk '{print $1}')"
echo "✅ Created: $ARCHIVE_FILE ($SIZE)"

# чистим старые архивы, храним только KEEP
all_archives=()
while IFS= read -r f; do
  all_archives+=("$f")
done < <(ls -t "$ARCHIVE_DIR"/commit_*.zip 2>/dev/null || true)

if (( ${#all_archives[@]} > KEEP )); then
  to_delete=( "${all_archives[@]:KEEP}" )
  for f in "${to_delete[@]}"; do
    rm -f -- "$f" || true
  done
  echo "🧹 Pruned old archives: kept $KEEP"
fi
