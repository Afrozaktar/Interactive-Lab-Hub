#!/usr/bin/env python3
"""
Minute Flower Clock

A fully bloomed 12-petal flower acts as a minute clock.

00 minutes -> petal 1
05 minutes -> petal 2
10 minutes -> petal 3
...
55 minutes -> petal 12

The butterfly/firefly moves smoothly around the flower.

06:00 AM - 06:59 PM -> butterfly
07:00 PM - 05:59 AM -> firefly
"""

import math
import time

import board
import digitalio
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7789 as st7789


# ============================================================
# DISPLAY SETUP
# ============================================================

cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)

BAUDRATE = 24000000

spi = board.SPI()

disp = st7789.ST7789(
    spi,
    rotation=90,
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
    WIDTH = disp.height
    HEIGHT = disp.width
else:
    WIDTH = disp.width
    HEIGHT = disp.height


# ============================================================
# COLOR HELPERS
# ============================================================

def hsb(h, s, b):
    """Convert HSB/HSV to RGB."""

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

    return (
        round((r + m) * 255),
        round((g + m) * 255),
        round((bl + m) * 255),
    )


def blend(fg, bg, alpha_pct):
    """Blend two colors."""

    a = max(0.0, min(1.0, alpha_pct / 100.0))

    return tuple(
        round(fg[i] * a + bg[i] * (1 - a))
        for i in range(3)
    )


# ============================================================
# SKY COLORS
# ============================================================

SKY_NIGHT = (0x22, 0x20, 0x59)
SKY_DAWN = (0xFF, 0xF7, 0xE0)
SKY_DAY = (0xD9, 0xFD, 0xFF)
SKY_SUNSET = (0xF7, 0x99, 0x40)


# ============================================================
# FLOWER COLORS
# ============================================================

# Softer, lighter pink flower
PETAL_OUTLINE = (188, 91, 151)
PETAL_FILL = (255, 181, 216)
PETAL_LIGHT = (255, 218, 237)
PETAL_SHADOW = (238, 139, 193)

# Warm yellow center
CENTER_COLOR = (245, 191, 62)
CENTER_HIGHLIGHT = (255, 211, 91)

# Stem / leaves
STEM_COLOR = hsb(120, 60, 40)
LEAF_COLOR = hsb(120, 70, 60)

# Blue butterfly
BUTTERFLY_COLOR = (91, 174, 235)
BUTTERFLY_LIGHT = (157, 216, 255)
BUTTERFLY_DARK = (55, 104, 172)

# Firefly
FIREFLY_BODY = hsb(55, 70, 35)
FIREFLY_GLOW = (255, 245, 110)

TEXT_COLOR = (230, 230, 230)


# ============================================================
# GEOMETRY
# ============================================================

# The important change:
# The petals are now narrower so each of the 12 petals
# remains visually separate.

FLOWER_RADIUS = 42

# Distance from flower center to petal center
PETAL_RADIUS = 25

# Narrower petals prevent overlap
PETAL_WIDTH = 6.5
PETAL_HEIGHT = 18

STEM_TOP = 35
STEM_BOTTOM = 145


# ============================================================
# GEOMETRY HELPERS
# ============================================================

def transform(lx, ly, angle, ox, oy):
    """Rotate and translate a point."""

    gx = (
        lx * math.cos(angle)
        - ly * math.sin(angle)
    )

    gy = (
        lx * math.sin(angle)
        + ly * math.cos(angle)
    )

    return (
        ox + gx,
        oy + gy
    )


def ellipse_points(
    rx,
    ry,
    angle,
    ox,
    oy,
    shift_y=0.0,
    n=24
):
    """Create points approximating a rotated ellipse."""

    pts = []

    for i in range(n):

        t = 2 * math.pi * i / n

        lx = rx * math.cos(t)

        ly = (
            ry * math.sin(t)
            + shift_y
        )

        pts.append(
            transform(
                lx,
                ly,
                angle,
                ox,
                oy
            )
        )

    return pts


# ============================================================
# TIME
# ============================================================

def get_local_time():
    return time.localtime()


def get_sky_color(local):
    """Return the sky color based on the current hour."""

    hour = local.tm_hour

    if 20 <= hour or hour < 5:
        return SKY_NIGHT

    elif 5 <= hour < 8:
        return SKY_DAWN

    elif 8 <= hour < 18:
        return SKY_DAY

    else:
        return SKY_SUNSET


# ============================================================
# MINUTE POSITION
# ============================================================

def minute_position(local):
    """
    Convert the current minute into a position around
    the 12-petal flower.

    00 -> petal 1
    05 -> petal 2
    10 -> petal 3
    ...
    55 -> petal 12

    Seconds are included for smooth movement.
    """

    minute_value = (
        local.tm_min
        + local.tm_sec / 60.0
    )

    return minute_value / 5.0


def animal_position(cx, cy, local):
    """Return x, y and angle for the butterfly/firefly."""

    pos = minute_position(local)

    # Petal 1 is at the top.
    # Movement is clockwise.
    angle = (
        -math.pi / 2
        + pos * 2 * math.pi / 12
    )

    x = (
        cx
        + FLOWER_RADIUS * math.cos(angle)
    )

    y = (
        cy
        + FLOWER_RADIUS * math.sin(angle)
    )

    return x, y, angle


# ============================================================
# FLOWER PETAL
# ============================================================

def draw_petal(draw, cx, cy, angle):
    """
    Draw one narrow, elegant petal.

    The petals are deliberately narrower than before.
    This creates a small gap between neighboring petals
    so all 12 can be seen individually.
    """

    # Position of this petal
    px = (
        cx
        + PETAL_RADIUS * math.cos(angle)
    )

    py = (
        cy
        + PETAL_RADIUS * math.sin(angle)
    )

    # --------------------------------------------------------
    # Outer petal
    # --------------------------------------------------------

    outer_pts = ellipse_points(
        PETAL_WIDTH,
        PETAL_HEIGHT,
        angle + math.pi / 2,
        px,
        py,
        n=24
    )

    draw.polygon(
        outer_pts,
        fill=PETAL_OUTLINE
    )

    # --------------------------------------------------------
    # Inner soft pink petal
    # --------------------------------------------------------

    inner_pts = ellipse_points(
        PETAL_WIDTH * 0.78,
        PETAL_HEIGHT * 0.86,
        angle + math.pi / 2,
        px,
        py,
        n=24
    )

    draw.polygon(
        inner_pts,
        fill=PETAL_FILL
    )

    # --------------------------------------------------------
    # Soft highlight on each petal
    # --------------------------------------------------------

    highlight_x = (
        px
        - 1.5 * math.sin(angle)
    )

    highlight_y = (
        py
        + 1.5 * math.cos(angle)
    )

    highlight_pts = ellipse_points(
        2.0,
        6.5,
        angle + math.pi / 2,
        highlight_x,
        highlight_y - 3,
        n=18
    )

    draw.polygon(
        highlight_pts,
        fill=PETAL_LIGHT
    )


# ============================================================
# FLOWER
# ============================================================

def draw_flower(draw, cx, cy):
    """Draw the complete 12-petal flower."""

    # --------------------------------------------------------
    # Stem
    # --------------------------------------------------------

    draw.line(
        (
            cx,
            cy + STEM_TOP,
            cx,
            cy + STEM_BOTTOM
        ),
        fill=STEM_COLOR,
        width=3
    )

    # --------------------------------------------------------
    # Left leaf
    # --------------------------------------------------------

    draw.ellipse(
        (
            cx - 30,
            cy + 70,
            cx - 3,
            cy + 84
        ),
        fill=LEAF_COLOR
    )

    # --------------------------------------------------------
    # Right leaf
    # --------------------------------------------------------

    draw.ellipse(
        (
            cx + 3,
            cy + 90,
            cx + 30,
            cy + 104
        ),
        fill=LEAF_COLOR
    )

    # --------------------------------------------------------
    # 12 petals
    # --------------------------------------------------------

    for i in range(12):

        angle = (
            -math.pi / 2
            + i * (2 * math.pi / 12)
        )

        draw_petal(
            draw,
            cx,
            cy,
            angle
        )

    # --------------------------------------------------------
    # Flower center
    # --------------------------------------------------------

    draw.ellipse(
        (
            cx - 12,
            cy - 12,
            cx + 12,
            cy + 12
        ),
        fill=CENTER_COLOR
    )

    # Small center highlight
    draw.ellipse(
        (
            cx - 5,
            cy - 7,
            cx + 2,
            cy - 1
        ),
        fill=CENTER_HIGHLIGHT
    )


# ============================================================
# BUTTERFLY
# ============================================================

def draw_butterfly(draw, x, y, angle, local):
    """
    Draw a small blue butterfly.

    The butterfly follows the minute position
    around the flower.
    """

    # Direction of movement
    dx = math.cos(angle)
    dy = math.sin(angle)

    # --------------------------------------------------------
    # Wing animation
    # --------------------------------------------------------

    flap = (
        math.sin(
            (local.tm_sec + time.time() % 1) * 8
        ) * 2
    )

    # Perpendicular direction
    px = -dy
    py = dx

    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

    draw.ellipse(
        (
            x - 2,
            y - 7,
            x + 2,
            y + 7
        ),
        fill=BUTTERFLY_DARK
    )

    # --------------------------------------------------------
    # Left wing
    # --------------------------------------------------------

    left_x = (
        x
        + px * (7 + flap)
    )

    left_y = (
        y
        + py * (7 + flap)
    )

    draw.ellipse(
        (
            left_x - 6,
            left_y - 5,
            left_x + 6,
            left_y + 5
        ),
        fill=BUTTERFLY_COLOR
    )

    # Small lighter part of wing
    draw.ellipse(
        (
            left_x - 3,
            left_y - 3,
            left_x + 3,
            left_y + 2
        ),
        fill=BUTTERFLY_LIGHT
    )

    # --------------------------------------------------------
    # Right wing
    # --------------------------------------------------------

    right_x = (
        x
        - px * (7 + flap)
    )

    right_y = (
        y
        - py * (7 + flap)
    )

    draw.ellipse(
        (
            right_x - 6,
            right_y - 5,
            right_x + 6,
            right_y + 5
        ),
        fill=BUTTERFLY_COLOR
    )

    # Small lighter part of wing
    draw.ellipse(
        (
            right_x - 3,
            right_y - 3,
            right_x + 3,
            right_y + 2
        ),
        fill=BUTTERFLY_LIGHT
    )

    # --------------------------------------------------------
    # Antennae
    # --------------------------------------------------------

    draw.line(
        (
            x - 1,
            y - 6,
            x - 5,
            y - 10
        ),
        fill=BUTTERFLY_DARK,
        width=1
    )

    draw.line(
        (
            x + 1,
            y - 6,
            x + 5,
            y - 10
        ),
        fill=BUTTERFLY_DARK,
        width=1
    )


# ============================================================
# FIREFLY
# ============================================================

def draw_firefly(draw, x, y, angle, local):
    """Draw a glowing firefly."""

    # Gentle glow animation
    pulse = (
        math.sin(
            (local.tm_sec + time.time() % 1) * 4
        ) + 1
    ) / 2

    glow_r = int(
        5 + pulse * 3
    )

    # Glow
    draw.ellipse(
        (
            x - glow_r,
            y - glow_r,
            x + glow_r,
            y + glow_r
        ),
        fill=blend(
            FIREFLY_GLOW,
            get_sky_color(local),
            25 + pulse * 25
        )
    )

    # Body
    draw.ellipse(
        (
            x - 3,
            y - 3,
            x + 3,
            y + 3
        ),
        fill=FIREFLY_BODY
    )

    # Wings
    draw.ellipse(
        (
            x - 7,
            y - 3,
            x - 2,
            y + 2
        ),
        fill=FIREFLY_GLOW
    )

    draw.ellipse(
        (
            x + 2,
            y - 3,
            x + 7,
            y + 2
        ),
        fill=FIREFLY_GLOW
    )


# ============================================================
# ANIMAL
# ============================================================

def draw_animal(draw, cx, cy, local):
    """Choose butterfly or firefly based on the hour."""

    x, y, angle = animal_position(
        cx,
        cy,
        local
    )

    # Butterfly:
    # 6 AM through 6:59 PM
    if 6 <= local.tm_hour < 19:

        draw_butterfly(
            draw,
            x,
            y,
            angle,
            local
        )

    # Firefly:
    # 7 PM through 5:59 AM
    else:

        draw_firefly(
            draw,
            x,
            y,
            angle,
            local
        )


# ============================================================
# MAIN
# ============================================================

def main():

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT)
    )

    draw = ImageDraw.Draw(image)

    # --------------------------------------------------------
    # Flower center
    # --------------------------------------------------------

    cx = WIDTH // 2
    cy = 65

    # --------------------------------------------------------
    # Animation loop
    # --------------------------------------------------------

    while True:

        local = get_local_time()

        # Sky
        bg_color = get_sky_color(local)

        draw.rectangle(
            (
                0,
                0,
                WIDTH,
                HEIGHT
            ),
            fill=bg_color
        )

        # Flower
        draw_flower(
            draw,
            cx,
            cy
        )

        # Butterfly / firefly
        draw_animal(
            draw,
            cx,
            cy,
            local
        )

        # Small minute label
        draw.text(
            (
                4,
                HEIGHT - 12
            ),
            f"{local.tm_min:02d}m",
            fill=TEXT_COLOR
        )

        # Send to display
        disp.image(image)

        # Smooth movement
        time.sleep(1 / 15)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
