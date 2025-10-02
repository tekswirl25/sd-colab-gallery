#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "❌ Error at line $LINENO"; exit 1' ERR

KEEP=${KEEP:-5}
HASH="${1:-HEAD}"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "❌ Not a git repository"; exit 1; }
cd "$repo_root"

if ! git rev-parse --verify "${HASH}^{commit}" >/dev/null 2>&1; then
  echo "❌ Invalid commit ref: $HASH"
  exit 1
fi

SHORT_HASH="$(git rev-parse --short "$HASH")"
ARCHIVE_DIR="$repo_root/archives"
ARCHIVE_FILE="$ARCHIVE_DIR/commit_${SHORT_HASH}.zip"
mkdir -p "$ARCHIVE_DIR"

# Все tracked файлы на коммите
FILES="$(git ls-tree -r --name-only "$HASH" || true)"

# Собрать все паттерны
EXC=()
if [[ -f "$repo_root/.archiveignore" ]]; then
  while IFS= read -r line; do
    [[ -z "${line//[[:space:]]/}" || "$line" =~ ^[[:space:]]*# ]] && continue
    EXC+=("$line")
  done < "$repo_root/.archiveignore"
fi

# Фильтрация файлов
FILTERED=""
while IFS= read -r f; do
  skip=0
  for pat in "${EXC[@]:-}"; do
    if [[ "$pat" =~ ^[\^\.\|\(\)\[\]\*\+\?\{\}] ]]; then
      # regex
      if echo "$f" | grep -Eq "$pat"; then
        skip=1; break
      fi
    else
      # glob
      if [[ "$f" == $pat ]]; then
        skip=1; break
      fi
    fi
  done
  (( skip == 0 )) && FILTERED+="$f"$'\n'
done <<< "$FILES"

if [[ -z "${FILTERED//[$'\t\r\n ']/}" ]]; then
  echo "ℹ️  No matching files to archive after filters."
  exit 0
fi

# Test
# echo "FILES before filter:"
# echo "$FILES" | head -20
# 
# echo "EXC patterns:"
# printf '%s\n' "${EXC[@]}" | head -20
#
# echo "FILES after filter:"
# echo "$FILTERED" | head -20
# end of test

# Упаковка
if command -v zip >/dev/null 2>&1; then
  echo "$FILTERED" | zip -q -@ "$ARCHIVE_FILE"
elif command -v 7z >/dev/null 2>&1; then
  tmpfile="$(mktemp)"; echo "$FILTERED" > "$tmpfile"
  7z a -tzip "$ARCHIVE_FILE" @"$tmpfile" >/dev/null; rm -f "$tmpfile"
else
  echo "❌ No archiver found (zip or 7z)."; exit 1
fi

# Добавить локальные git hooks
if [[ -d "$repo_root/.git/hooks" ]]; then
  zip -qr "$ARCHIVE_FILE" .git/hooks -x "*.sample"
fi

SIZE="$(du -h "$ARCHIVE_FILE" | awk '{print $1}')"
echo "✅ Created: $ARCHIVE_FILE ($SIZE)"

# Чистка старых архивов
all_archives=$(ls -t "$ARCHIVE_DIR"/commit_*.zip 2>/dev/null || true)
count=$(echo "$all_archives" | wc -w | tr -d ' ')
if (( count > KEEP )); then
  to_delete=$(echo "$all_archives" | awk "{if (NR>$KEEP) print}")
  for f in $to_delete; do rm -f -- "$f" || true; done
  echo "🧹 Pruned old archives: kept $KEEP"
fi
