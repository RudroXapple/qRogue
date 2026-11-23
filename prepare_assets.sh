#!/bin/bash
set -e
SRC="${1:-$HOME/flipper-x-rogue/qFlipper/application/assets}"
SUDO=""; [ "$(id -u)" != "0" ] && SUDO="sudo"
$SUDO apt-get update && $SUDO apt-get install -y librsvg2-bin
mkdir -p assets/fonts assets/gfx
cp "$SRC"/fonts/Born2bSportyV2.ttf \
   "$SRC"/fonts/ProggySquare.ttf \
   "$SRC"/fonts/ShareTech-Regular.ttf \
   "$SRC"/fonts/ShareTechMono-Regular.ttf assets/fonts/
convert_svg() {
    rsvg-convert -w $(( $3 * 2 )) -h $(( $4 * 2 )) "$SRC/gfx/$2" -o "assets/gfx/$1.png"
    echo "ok: $1.png"
}
convert_svg flipper     images/flipper.svg          360 156
convert_svg default     images/default.svg          128 64
convert_svg typec       images/typec.svg            159 37
convert_svg spinner     images/spinner.svg          24  24
convert_svg info-small  symbolic/info-small.svg     22  22
convert_svg arrow-up    symbolic/arrow-up.svg       24  24
convert_svg arrow-down  symbolic/arrow-down.svg     24  24
echo "Done. Assets are in ./assets"
