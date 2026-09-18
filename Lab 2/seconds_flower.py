#!/usr/bin/env python3
"""
flower_clock_seconds.py

Seconds flower from Lamiah Khan's "Flower Clock"
(https://github.com/khanlamiah019/the_flower_clock), ported from p5.js to
run on the Adafruit Mini PiTFT - 135x240 Color TFT Add-on for Raspberry Pi
(ST7789, SPI): https://www.adafruit.com/product/4393

This keeps the original bloom math from the sketch.js drawPinkFlower() /
drawBlueFlower() functions: the same petal-count, petal-growth, and
bud-fade formulas, and the same "a new leaf appears every 15 seconds"
logic -- just recolored blue (like the original minutes flower), redrawn
with Pillow instead of p5.js canvas calls, and rescaled (~0.42x) to fit
the display's small 240x135 area instead of the original 800x600 canvas.

The background is no longer a fixed dark color -- it now shifts with
the time of day, same as the hour flower:

     8:00 PM - 4:59:59 AM  -> #222059  (night)
     5:00 AM - 7:59:59 AM  -> #FFF7E0  (sunrise)
     8:00 AM - 5:59:59 PM  -> #D9FDFF  (day)
     6:00 PM - 7:59:59 PM  -> #F79940  (sunset)

--------------------------------------------------------------------------
ONE-TIME SETUP ON THE PI  (skip anything you've already done)
--------------------------------------------------------------------------
    sudo raspi-config          # Interface Options -> SPI -> Enable
    pip3 install adafruit-circuitpython-rgb-display pillow adafruit-blinka

    # If you hit "lgpio.error: 'GPIO busy'" on board.CE0, add this line to
    # /boot/firmware/config.txt under the [all] section, then reboot:
    #     dtoverlay=spi0-0cs

Run:
    python flower_clock_seconds.py

    Use Ctrl+C to quit -- NOT Ctrl+Z. Ctrl+Z only suspends the process
    (it keeps holding the GPIO pins), which causes "GPIO busy" errors on
    the next run. Ctrl+C actually terminates it and releases the pins.
--------------------------------------------------------------------------
"""

import math
import time

import board
import digitalio
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7789 as st7789


# ------------------------------------------------------- display setup
# CS/DC/RST pins and the width/height/offset values are Adafruit's own
# documented defaults for the Mini PiTFT 1.14" (135x240):
# https://learn.adafruit.com/adafruit-mini-pitft-135x240-color-tft-add-on-for-raspberry-pi/python-usage
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)
BAUDRATE = 24000000

spi = board.SPI()

disp = st7789.ST7789(
    spi,
    rotation=90,        # landscape
    width=135,
    height=240,
    x_offset=53,
    y_offset=40,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
)

if disp.rotation % 180 == 90:
    WIDTH = disp.height   # 240
    HEIGHT = disp.width   # 135
else:
    WIDTH = disp.width
    HEIGHT = disp.height


# ---------------------------------------------------------------- colors
def hsb(h, s, b):
    """HSB/HSV (h: 0-360, s/b: 0-100) -> RGB (0-255). Same color model as
    p5.js's colorMode(HSB, 360, 100, 100), so the hue/sat/bright values
    below match the ones used in sketch.js directly."""
    h = (h % 360) / 60.0
    s /= 100.0
    b /= 100.0
    c = b * s
    x = c * (1 - abs(h % 2 - 1))
    m = b - c
    if 0 <= h < 1:
        r, g, bl = c, x, 0
    elif 1 <= h < 2:
        r, g, bl = x, c, 0
    elif 2 <= h < 3:
        r, g, bl = 0, c, x
    elif 3 <= h < 4:
        r, g, bl = 0, x, c
    elif 4 <= h < 5:
        r, g, bl = x, 0, c
    else:
        r, g, bl = c, 0, x
    return (round((r + m) * 255), round((g + m) * 255), round((bl + m) * 255))


def blend(fg, bg, alpha_pct):
    """Blend fg over bg at alpha_pct (0-100). Approximates p5.js's
    fill(..., alpha) transparency for the bud overlay, since Pillow's
    ImageDraw doesn't alpha-composite onto a plain RGB image."""
    a = max(0.0, min(1.0, alpha_pct / 100.0))
    return tuple(round(fg[i] * a + bg[i] * (1 - a)) for i in range(3))


def hex_to_rgb(hex_str):
    """Convert a '#RRGGBB' string to an (r, g, b) tuple."""
    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i + 2], 16) for i in (0, 2, 4))


# --------------------------------------------------- sky / background
# 8:00 PM - 4:59:59 AM  -> #222059  (night)
# 5:00 AM - 7:59:59 AM  -> #FFF7E0  (sunrise)
# 8:00 AM - 5:59:59 PM  -> #D9FDFF  (day)
# 6:00 PM - 7:59:59 PM  -> #F79940  (sunset)

NIGHT_SKY_COLOR   = hex_to_rgb("#222059")
SUNRISE_SKY_COLOR = hex_to_rgb("#FFF7E0")
DAY_SKY_COLOR     = hex_to_rgb("#D9FDFF")
SUNSET_SKY_COLOR  = hex_to_rgb("#F79940")


def get_sky_color(hour_value):
    """
    Return the sky/background color for the given hour_value
    (hours elapsed since midnight, 0.0 - 24.0).
    """
    h = hour_value % 24

    if h >= 20 or h < 5:
        return NIGHT_SKY_COLOR
    elif h < 8:
        return SUNRISE_SKY_COLOR
    elif h < 18:
        return DAY_SKY_COLOR
    else:
        return SUNSET_SKY_COLOR


def day_progress(now=None):
    """Hours elapsed since midnight (0.0 - 24.0), used only to pick the
    sky color -- unrelated to the seconds-flower bloom timer below."""
    now = now if now is not None else time.time()
    local = time.localtime(now)
    seconds_today = local.tm_hour * 3600 + local.tm_min * 60 + local.tm_sec
    return seconds_today / 3600.0


STEM_COLOR = hsb(120, 60, 40)
LEAF_COLOR = hsb(120, 70, 60)
CENTER_COLOR = hsb(45, 90, 80)
PETAL_FILL = hsb(220, 50, 85)        # blue, like the original minutes flower
PETAL_STROKE = hsb(220, 80, 40)
PETAL_HIGHLIGHT = hsb(220, 30, 95)
BUD_COLOR = hsb(120, 40, 50)
BUD_TIP_COLOR = hsb(120, 60, 30)
TEXT_COLOR = (230, 230, 230)


# ------------------------------------------------------------ geometry
def transform(lx, ly, angle, ox, oy):
    """Rotate local point (lx, ly) by angle (p5-style, y-down screen
    coords) then translate to (ox, oy) -- mirrors p5.js's rotate()+
    translate() matrix composition."""
    gx = lx * math.cos(angle) - ly * math.sin(angle)
    gy = lx * math.sin(angle) + ly * math.cos(angle)
    return (ox + gx, oy + gy)


def ellipse_points(rx, ry, angle, ox, oy, shift_y=0.0, n=14):
    """Points approximating an ellipse (radii rx, ry) centered at local
    (0, shift_y), rotated by angle, then placed at (ox, oy). shift_y is
    how far p5's translate() moved the ellipse before rotate() was
    applied (used for petals; 0 for leaves)."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        lx = rx * math.cos(t)
        ly = ry * math.sin(t) + shift_y
        pts.append(transform(lx, ly, angle, ox, oy))
    return pts


# ---------------------------------------------------------------- scale
# sketch.js's seconds flower was drawn at size=60 with a ~130px stem on
# an 800x600 canvas. Scaled down to fit this display's 240x135 area.
SCALE = 0.42
FLOWER_SIZE = 60 * SCALE
STEM_TOP = 20 * SCALE
STEM_BOTTOM = 150 * SCALE
PETAL_COUNT = 8


def bloom_progress(now=None):
    now = now if now is not None else time.time()
    local = time.localtime(now)
    frac = now - math.floor(now)
    seconds_elapsed = local.tm_sec + frac
    return seconds_elapsed


def draw_leaves(draw, cx, cy, second_value):
    """Matches sketch.js's drawDynamicLeaves(): a new leaf every 15
    seconds, alternating sides, growing slightly with each one."""
    num_leaves = int(second_value // 15) + 2
    for i in range(num_leaves):
        leaf_y = (80 * SCALE) + i * (15 * SCALE)
        side = -1 if i % 2 == 0 else 1
        leaf_x = side * ((10 + i * 3) * SCALE)
        leaf_rot = side * (0.2 + i * 0.1)
        leaf_w = (20 + i * 2) * SCALE
        leaf_h = (12 + i * 1) * SCALE
        pts = ellipse_points(leaf_w / 2, leaf_h / 2, leaf_rot,
                              cx + leaf_x, cy + leaf_y, n=10)
        draw.polygon(pts, fill=LEAF_COLOR)


def draw_petal(draw, cx, cy, angle, petal_dist, cur_w, cur_h):
    """Matches sketch.js's per-petal drawing: filled body + darker
    outline ring + lighter inner highlight."""
    stroke_pts = ellipse_points(cur_w / 2 * 1.18, cur_h / 2 * 1.10, angle,
                                 cx, cy, shift_y=-petal_dist, n=16)
    draw.polygon(stroke_pts, fill=PETAL_STROKE)

    fill_pts = ellipse_points(cur_w / 2, cur_h / 2, angle, cx, cy,
                               shift_y=-petal_dist, n=16)
    draw.polygon(fill_pts, fill=PETAL_FILL)

    hi_pts = ellipse_points(cur_w * 0.6 / 2, cur_h * 0.7 / 2, angle,
                             cx, cy, shift_y=-petal_dist + cur_h * 0.1, n=12)
    draw.polygon(hi_pts, fill=PETAL_HIGHLIGHT)


def draw_seconds_flower(draw, cx, cy, second_value, sky_color):
    bloom = min(1.0, max(0.0, second_value / 59.0))

    # Stem
    draw.line((cx, cy + STEM_TOP, cx, cy + STEM_BOTTOM),
              fill=STEM_COLOR, width=max(2, round(8 * SCALE)))

    # Leaves -- a new one every 15 seconds
    draw_leaves(draw, cx, cy, second_value)

    # Flower center (drawn before petals, same order as sketch.js)
    center_r = (6 + bloom * 15) * SCALE / 2
    draw.ellipse((cx - center_r, cy - center_r, cx + center_r, cy + center_r),
                 fill=CENTER_COLOR)

    # Petals
    base_radius = FLOWER_SIZE * 0.3
    bloom_radius = FLOWER_SIZE * (0.3 + bloom * 0.4)
    petal_w = (20 + bloom * 15) * SCALE
    petal_h = (40 + bloom * 30) * SCALE
    petal_dist = base_radius + (bloom_radius - base_radius) * bloom
    cur_w = petal_w * (0.3 + 0.7 * bloom)
    cur_h = petal_h * (0.4 + 0.6 * bloom)

    for i in range(PETAL_COUNT):
        angle = 2 * math.pi * i / PETAL_COUNT
        draw_petal(draw, cx, cy, angle, petal_dist, cur_w, cur_h)

    # Bud overlay while mostly closed -- fades out as it blooms.
    # Blended against the current sky color so it disappears cleanly
    # regardless of time of day.
    if bloom < 0.3:
        alpha = (1 - bloom * 3) * 80
        rx, ry = (25 * SCALE) / 2, (45 * SCALE) / 2
        by = cy - 10 * SCALE
        draw.ellipse((cx - rx, by - ry, cx + rx, by + ry),
                     fill=blend(BUD_COLOR, sky_color, alpha))

        alpha_tip = (1 - bloom * 3) * 90
        rx2, ry2 = (15 * SCALE) / 2, (20 * SCALE) / 2
        by2 = cy - 25 * SCALE
        draw.ellipse((cx - rx2, by2 - ry2, cx + rx2, by2 + ry2),
                     fill=blend(BUD_TIP_COLOR, sky_color, alpha_tip))


def main():
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    cx = WIDTH // 2
    cy = 40   # flower head near the top; stem + leaves hang below it

    while True:
        seconds_elapsed = bloom_progress()
        sky_color = get_sky_color(day_progress())

        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=sky_color)
        draw_seconds_flower(draw, cx, cy, seconds_elapsed, sky_color)
        draw.text((4, HEIGHT - 12), f"{int(seconds_elapsed):02d}s", fill=TEXT_COLOR)

        disp.image(image)
        time.sleep(1 / 15)   # Adafruit measured ~15 FPS max on this display


if __name__ == "__main__":
    main()
