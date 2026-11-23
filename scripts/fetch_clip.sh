#!/usr/bin/env bash
# Download one stock clip and print its technical facts.
#
#   ./fetch_clip.sh 4595479                 # Pexels video id -> raw/4595479.mp4
#   ./fetch_clip.sh 4595479 ./clips         # choose output dir
#   ./fetch_clip.sh https://.../file.mp4    # any direct URL
#   ./fetch_clip.sh https://www.pexels.com/video/xxxx-4595479/   # page URL works too
#
# Pexels needs a browser-like User-Agent on the download endpoint, and the
# endpoint answers 302 to the CDN, so -L is required.
set -euo pipefail

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
TARGET="${1:?usage: fetch_clip.sh <pexels-id|url> [outdir]}"
OUTDIR="${2:-raw}"
mkdir -p "$OUTDIR"

find_ffmpeg() {
  if [[ -n "${FFMPEG:-}" && -x "${FFMPEG}" ]]; then echo "$FFMPEG"; return; fi
  if command -v ffmpeg >/dev/null 2>&1; then command -v ffmpeg; return; fi
  python3 - <<'PY' 2>/dev/null && return
import imageio_ffmpeg
print(imageio_ffmpeg.get_ffmpeg_exe())
PY
  echo ""
}
FF="$(find_ffmpeg)"

probe() {
  [[ -n "$FF" ]] || { echo "  (ffmpeg not found, skipping probe)"; return; }
  "$FF" -hide_banner -i "$1" 2>&1 | grep -E "Duration|Stream #0:0" | sed 's/^/  /'
}

case "$TARGET" in
  http*)
    if [[ "$TARGET" =~ /video/.+-([0-9]+)/?$ ]]; then
      id="${BASH_REMATCH[1]}"
      url=$(curl -s -A "$UA" -D - -o /dev/null --max-time 30 \
            "https://www.pexels.com/download/video/${id}/" \
            | awk 'tolower($1)=="location:"{print $2}' | tr -d '\r')
      [[ -n "$url" ]] || { echo "could not resolve download url for id $id" >&2; exit 1; }
      name="$id"
    else
      url="$TARGET"
      name=$(basename "${TARGET%%\?*}")
    fi
    ;;
  *[!0-9]*|"")
    echo "not a Pexels id or URL: $TARGET" >&2; exit 1
    ;;
  *)
    id="$TARGET"
    url=$(curl -s -A "$UA" -D - -o /dev/null --max-time 30 \
          "https://www.pexels.com/download/video/${id}/" \
          | awk 'tolower($1)=="location:"{print $2}' | tr -d '\r')
    [[ -n "$url" ]] || { echo "could not resolve download url for id $id" >&2; exit 1; }
    name="$id"
    ;;
esac

ext="${url##*.}"
[[ "$ext" == "$url" || ${#ext} -gt 5 ]] && ext=mp4
dest="$OUTDIR/${name%.*}.${ext}"
echo "-> $dest"
curl -sL -A "$UA" --max-time 600 -o "$dest" "$url"
[[ -s "$dest" ]] || { echo "download failed (empty file)" >&2; exit 1; }
ls -lh "$dest" | awk '{print "  size", $5}'
probe "$dest"
