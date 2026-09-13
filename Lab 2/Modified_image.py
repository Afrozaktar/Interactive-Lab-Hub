# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
from pathlib import Path
import board
import digitalio
from PIL import Image, ImageOps
from adafruit_rgb_display import st7789

# Find pictures in the same folder as this script.
folder = Path(__file__).resolve().parent

def load_picture(filename):
    path = folder / filename
    if not path.is_file():
        raise SystemExit(f"Picture not found: {path}")
    with Image.open(path) as picture:
        picture = ImageOps.exif_transpose(picture).convert("RGB")
        return ImageOps.fit(picture, (240, 135))

# Load both pictures before setting up the screen.
picture_a = load_picture("red.jpg")
picture_b = load_picture("earthing.jpg")

# Set up the display using your working GPIO settings.
cs_pin = digitalio.DigitalInOut(board.D5)
dc_pin = digitalio.DigitalInOut(board.D25)
spi = board.SPI()

disp = st7789.ST7789(
    spi,
    cs=cs_pin,
    dc=dc_pin,
    rst=None,
    baudrate=24000000,
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
)

# Turn on the display backlight.
backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output(value=True)

# Buttons read False when pressed.
buttonA = digitalio.DigitalInOut(board.D23)
buttonB = digitalio.DigitalInOut(board.D24)
buttonA.switch_to_input(pull=digitalio.Pull.UP)
buttonB.switch_to_input(pull=digitalio.Pull.UP)

current_picture = "A"

try:
    # Start with the first picture.
    disp.image(picture_a, rotation=90)
    print("Press A for red.jpg or B for earthing.jpg.")
    print("Press Ctrl+C in PuTTY to stop.")

    while True:
        a_pressed = not buttonA.value
        b_pressed = not buttonB.value

        if a_pressed and not b_pressed:
            if current_picture != "A":
                disp.image(picture_a, rotation=90)
                current_picture = "A"

        elif b_pressed and not a_pressed:
            if current_picture != "B":
                disp.image(picture_b, rotation=90)
                current_picture = "B"

        # Keep the selected picture when buttons are released.
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Stopped.")

finally:
    # Release the pins when the program stops.
    backlight.value = False
    buttonA.deinit()
    buttonB.deinit()
    backlight.deinit()
    cs_pin.deinit()
    dc_pin.deinit()
    spi.deinit()