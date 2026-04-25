#!/bin/bash
# Theme 1 — assemble final MP4
set -e

ROOT="/Users/sridharsuresh/Documents/ai-for-bharat/docs/video-output/theme1"
AUDIO="$ROOT/audio"
SLIDES="$ROOT/slides"
OUT="$ROOT/theme1-demo.mp4"
TMP="$ROOT/.tmp"

FFMPEG="/Users/sridharsuresh/Documents/ai-for-bharat/docs/video-output/bin/ffmpeg"
FFPROBE="/Users/sridharsuresh/Documents/ai-for-bharat/docs/video-output/bin/ffprobe"

mkdir -p "$TMP"
rm -f "$TMP"/*.mp4 "$TMP"/concat.txt

echo "Step 1/3 — making per-slide MP4s..."
for i in 01 02 03 04 05 06 07 08 09; do
  PNG="$SLIDES/slide_${i}.png"
  AIFF="$AUDIO/unit_${i}.aiff"
  OUT_SEG="$TMP/seg_${i}.mp4"
  DUR=$("$FFPROBE" -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AIFF")
  echo "  seg $i — ${DUR}s"
  "$FFMPEG" -y -loop 1 -i "$PNG" -i "$AIFF" \
    -c:v libx264 -tune stillimage -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 192k -shortest \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0a1f2c" \
    -t "$DUR" \
    "$OUT_SEG" -loglevel error
done

echo "Step 2/3 — concatenating..."
> "$TMP/concat.txt"
for i in 01 02 03 04 05 06 07 08 09; do
  echo "file '$TMP/seg_${i}.mp4'" >> "$TMP/concat.txt"
done
"$FFMPEG" -y -f concat -safe 0 -i "$TMP/concat.txt" -c copy "$OUT" -loglevel error

echo "Step 3/3 — cleanup..."
rm -rf "$TMP"
echo ""
echo "✓ Done: $OUT"
ls -lh "$OUT"
