#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Compile the DIY_SPOT_WELDER_V1 firmware for the Arduino Nano (ATmega328P, 16 MHz) without the
# Arduino IDE. Used in CI / the cloud environment. Normal users: open the sketch folder in the
# Arduino IDE 2.x (board "Arduino Nano", processor "ATmega328P") or use arduino-cli:
#   arduino-cli compile --fqbn arduino:avr:nano:cpu=atmega328 Firmware/Source/DIY_SPOT_WELDER_V1
#
# Env: ARDUINO_AVR (core dir), LIBS (dir containing Adafruit_SSD1306, Adafruit-GFX-Library, Adafruit_BusIO)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CORE="${ARDUINO_AVR:-/usr/share/arduino/hardware/arduino/avr}"
LIBS="${LIBS:-/tmp/claude-0/libs}"
SK="$HERE/Source/DIY_SPOT_WELDER_V1"
OUT="$HERE/build/avr"
rm -rf "$OUT"; mkdir -p "$OUT"
MCU=atmega328p
DEF="-DF_CPU=16000000L -DARDUINO=10819 -DARDUINO_AVR_NANO -DARDUINO_ARCH_AVR"
INC="-I$CORE/cores/arduino -I$CORE/variants/eightanaloginputs -I$CORE/libraries/Wire/src -I$CORE/libraries/Wire/src/utility \
 -I$CORE/libraries/EEPROM/src -I$CORE/libraries/SPI/src -I$LIBS/Adafruit_SSD1306 -I$LIBS/Adafruit-GFX-Library -I$LIBS/Adafruit_BusIO -I$SK"
CF="-c -g -Os -Wall -Wextra -ffunction-sections -fdata-sections -flto -mmcu=$MCU $DEF $INC"
CXXF="$CF -std=gnu++11 -fpermissive -fno-exceptions -fno-threadsafe-statics -Wno-error=narrowing"
objs=()
compile() {  # src
    local s="$1" o="$OUT/$(echo "$1" | md5sum | cut -c1-8)_$(basename "$1").o"
    case "$s" in
        *.c)   avr-gcc $CF -std=gnu11 "$s" -o "$o" ;;
        *.S)   avr-gcc -c -g -x assembler-with-cpp -flto -mmcu=$MCU $DEF $INC "$s" -o "$o" ;;
        *)     avr-g++ $CXXF -x c++ "$s" -o "$o" ;;
    esac
    objs+=("$o")
}
for f in "$CORE"/cores/arduino/*.{c,cpp,S}; do [ -e "$f" ] && compile "$f"; done 2>"$OUT/core_warnings.txt"
# link the core as an archive (like the Arduino IDE) so unused objects (e.g. Serial) are dropped
avr-gcc-ar rcs "$OUT/core.a" "${objs[@]}"; objs=()
for f in "$CORE"/libraries/Wire/src/Wire.cpp "$CORE"/libraries/Wire/src/utility/twi.c "$CORE"/libraries/SPI/src/SPI.cpp \
         "$LIBS"/Adafruit_SSD1306/Adafruit_SSD1306.cpp "$LIBS"/Adafruit-GFX-Library/Adafruit_GFX.cpp \
         "$LIBS"/Adafruit_BusIO/Adafruit_I2CDevice.cpp "$LIBS"/Adafruit_BusIO/Adafruit_SPIDevice.cpp; do
    compile "$f"
done 2>"$OUT/lib_warnings.txt"
# sketch (warnings shown)
for f in "$SK"/DIY_SPOT_WELDER_V1.ino "$SK"/*.cpp; do
    if [[ "$f" == *.ino ]]; then
        cp "$f" "$OUT/sketch.cpp"; sed -i '1i #include <Arduino.h>' "$OUT/sketch.cpp"; compile "$OUT/sketch.cpp"
    else compile "$f"; fi
done
avr-gcc -w -Os -g -flto -fuse-linker-plugin -Wl,--gc-sections -mmcu=$MCU -o "$OUT/DIY_SPOT_WELDER_V1.elf" "${objs[@]}" "$OUT/core.a" -lm
avr-objcopy -O ihex -R .eeprom "$OUT/DIY_SPOT_WELDER_V1.elf" "$OUT/DIY_SPOT_WELDER_V1.hex"
avr-size -C --mcu=$MCU "$OUT/DIY_SPOT_WELDER_V1.elf" | tee "$OUT/size.txt"
