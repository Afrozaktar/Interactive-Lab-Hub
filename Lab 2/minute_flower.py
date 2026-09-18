#!/usr/bin/env python3
"""
Orchid Flower Clock - Minute Version

The orchid blooms gradually over 60 minutes.

00:00  -> closed bud
15:00  -> partially bloomed
30:00  -> half bloomed
45:00  -> mostly bloomed
59:59  -> fully bloomed
00:00  -> resets to closed bud

Runs on the Adafruit Mini PiTFT 135x240 ST7789 display.
"""

import math
import time

import board
import digitalio
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7789 as st7789


# -------------------------------------------------------
# DISPLAY SETUP
# -------------------------------------------------------

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


# -------------------------------------------------------
# COLORS
# -------------------------------------------------------

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


# -------------------------------------------------------
# ORCHID COLORS
# -------------------------------------------------------

BG_COLOR = hsb(220, 20, 15)

# Stem and leaves
STEM_COLOR = hsb(120, 60, 40)
LEAF_COLOR = hsb(120, 70, 60)

# Pink orchid petals
PETAL_FILL = hsb(325, 55, 95)
PETAL_STROKE = hsb(320, 75, 55)
PETAL_HIGHLIGHT = hsb(330, 25, 100)

# Orchid center / lip
CENTER_COLOR = hsb(45, 90, 90)
LIP_COLOR = hsb(320, 80, 80)
LIP_DARK = hsb(315, 85, 50)
LIP_HIGHLIGHT = hsb(45, 80, 95)

# Pink bud
BUD_COLOR = hsb(325, 60, 70)
BUD_TIP_COLOR = hsb(315, 75, 45)

TEXT_COLOR = (230, 230, 230)





# -------------------------------------------------------
# GEOMETRY
# -------------------------------------------------------

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
    n=14
):
    """Create points approximating a rotated ellipse."""

    pts = []

    for i in range(n):

        t = (
            2 * math.pi * i / n
        )

        lx = (
            rx * math.cos(t)
        )

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


# -------------------------------------------------------
# SCALE
# -------------------------------------------------------

SCALE = 0.42

FLOWER_SIZE = 60 * SCALE

STEM_TOP = 20 * SCALE
STEM_BOTTOM = 150 * SCALE


# -------------------------------------------------------
# MINUTE TIMER
# -------------------------------------------------------

def bloom_progress(now=None):
    """
    Return how many minutes have elapsed in the current hour.

    0:00 -> 0.0
    0:15 -> 15.0
    0:30 -> 30.0
    0:45 -> 45.0
    0:59 -> 59.0

    The flower resets at the beginning of every hour.
    """

    if now is None:
        now = time.time()

    local = time.localtime(now)

    # Include seconds so the flower opens smoothly.
    minutes_elapsed = (
        local.tm_min
        + local.tm_sec / 60.0
    )

    return minutes_elapsed


# -------------------------------------------------------
# LEAVES
# -------------------------------------------------------

def draw_leaves(
    draw,
    cx,
    cy,
    minute_value
):
    """
    Add leaves as the orchid grows.

    A new leaf appears every 15 minutes.
    Maximum of 4 leaves.
    """

    num_leaves = (
        int(minute_value // 15)
        + 1
    )

    num_leaves = min(
        num_leaves,
        4
    )

    for i in range(num_leaves):

        leaf_y = (
            80 * SCALE
            + i * (15 * SCALE)
        )

        side = (
            -1 if i % 2 == 0
            else 1
        )

        leaf_x = (
            side
            * ((10 + i * 3) * SCALE)
        )

        leaf_rot = (
            side
            * (0.2 + i * 0.1)
        )

        leaf_w = (
            (20 + i * 2)
            * SCALE
        )

        leaf_h = (
            (12 + i)
            * SCALE
        )

        pts = ellipse_points(
            leaf_w / 2,
            leaf_h / 2,
            leaf_rot,
            cx + leaf_x,
            cy + leaf_y,
            n=10
        )

        draw.polygon(
            pts,
            fill=LEAF_COLOR
        )


# -------------------------------------------------------
# ORCHID PETAL
# -------------------------------------------------------

def draw_orchid_petal(
    draw,
    cx,
    cy,
    angle,
    distance,
    width,
    height
):
    """
    Draw one broad, rounded orchid petal.
    """

    # Dark purple outer edge
    outer = ellipse_points(
        width / 2,
        height / 2,
        angle,
        cx,
        cy,
        shift_y=-distance,
        n=20
    )

    draw.polygon(
        outer,
        fill=PETAL_STROKE
    )

    # Main purple petal
    inner = ellipse_points(
        width / 2 * 0.88,
        height / 2 * 0.88,
        angle,
        cx,
        cy,
        shift_y=-distance,
        n=20
    )

    draw.polygon(
        inner,
        fill=PETAL_FILL
    )

    # Light center highlight
    highlight = ellipse_points(
        width * 0.30,
        height * 0.32,
        angle,
        cx,
        cy,
        shift_y=(
            -distance
            - height * 0.08
        ),
        n=16
    )

    draw.polygon(
        highlight,
        fill=PETAL_HIGHLIGHT
    )


# -------------------------------------------------------
# ORCHID FLOWER
# -------------------------------------------------------

def draw_minutes_flower(
    draw,
    cx,
    cy,
    minute_value
):
    """
    Draw an orchid based on progress through the hour.

    0.0 = closed
    1.0 = fully open
    """

    # ---------------------------------------------------
    # BLOOM PROGRESS
    # ---------------------------------------------------

    bloom = (
        minute_value / 59.999
    )

    bloom = max(
        0.0,
        min(1.0, bloom)
    )

    # ---------------------------------------------------
    # STEM
    # ---------------------------------------------------

    draw.line(
        (
            cx,
            cy + STEM_TOP,
            cx,
            cy + STEM_BOTTOM
        ),
        fill=STEM_COLOR,
        width=max(
            2,
            round(8 * SCALE)
        )
    )

    # ---------------------------------------------------
    # LEAVES
    # ---------------------------------------------------

    draw_leaves(
        draw,
        cx,
        cy,
        minute_value
    )

    # ---------------------------------------------------
    # ORCHID PETAL SIZE
    # ---------------------------------------------------

    base_radius = (
        FLOWER_SIZE * 0.15
    )

    bloom_radius = (
        FLOWER_SIZE
        * (0.15 + bloom * 0.45)
    )

    petal_w = (
        (28 + bloom * 28)
        * SCALE
    )

    petal_h = (
        (38 + bloom * 30)
        * SCALE
    )

    petal_dist = (
        base_radius
        + (
            bloom_radius
            - base_radius
        ) * bloom
    )

    cur_w = (
        petal_w
        * (0.35 + 0.65 * bloom)
    )

    cur_h = (
        petal_h
        * (0.40 + 0.60 * bloom)
    )

    # ---------------------------------------------------
    # TOP SEPAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        cx,
        cy,
        0,
        petal_dist * 0.9,
        cur_w * 0.85,
        cur_h * 1.15
    )

    # ---------------------------------------------------
    # LEFT LARGE PETAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        cx,
        cy,
        math.radians(72),
        petal_dist,
        cur_w * 1.25,
        cur_h
    )

    # ---------------------------------------------------
    # RIGHT LARGE PETAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        cx,
        cy,
        math.radians(-72),
        petal_dist,
        cur_w * 1.25,
        cur_h
    )

    # ---------------------------------------------------
    # BOTTOM LEFT SEPAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        cx,
        cy,
        math.radians(150),
        petal_dist * 0.9,
        cur_w * 0.8,
        cur_h * 0.9
    )

    # ---------------------------------------------------
    # BOTTOM RIGHT SEPAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        cx,
        cy,
        math.radians(-150),
        petal_dist * 0.9,
        cur_w * 0.8,
        cur_h * 0.9
    )

    # ---------------------------------------------------
    # ORCHID CENTER / LIP
    # ---------------------------------------------------

    if bloom > 0.15:

        lip_w = (
            (16 + bloom * 14)
            * SCALE
        )

        lip_h = (
            (18 + bloom * 18)
            * SCALE
        )

        # Dark throat
        lip_outer = ellipse_points(
            lip_w,
            lip_h,
            0,
            cx,
            cy + 3 * SCALE,
            n=16
        )

        draw.polygon(
            lip_outer,
            fill=LIP_DARK
        )

        # Purple/pink lip
        lip_inner = ellipse_points(
            lip_w * 0.72,
            lip_h * 0.72,
            0,
            cx,
            cy + 4 * SCALE,
            n=16
        )

        draw.polygon(
            lip_inner,
            fill=LIP_COLOR
        )

        # Yellow/orange throat
        throat_w = (
            (5 + bloom * 5)
            * SCALE
        )

        throat_h = (
            (6 + bloom * 7)
            * SCALE
        )

        draw.ellipse(
            (
                cx - throat_w,
                cy - 1 * SCALE,
                cx + throat_w,
                cy + throat_h
            ),
            fill=LIP_HIGHLIGHT
        )

    # ---------------------------------------------------
    # CLOSED-BUD OVERLAY
    # ---------------------------------------------------

    if bloom < 0.30:

        alpha = (
            (1 - bloom * 3)
            * 80
        )

        rx = (
            25 * SCALE
        ) / 2

        ry = (
            45 * SCALE
        ) / 2

        by = (
            cy - 10 * SCALE
        )

        draw.ellipse(
            (
                cx - rx,
                by - ry,
                cx + rx,
                by + ry
            ),
            fill=blend(
                BUD_COLOR,
                BG_COLOR,
                alpha
            )
        )

        # Darker bud tip
        alpha_tip = (
            (1 - bloom * 3)
            * 90
        )

        rx2 = (
            15 * SCALE
        ) / 2

        ry2 = (
            20 * SCALE
        ) / 2

        by2 = (
            cy - 25 * SCALE
        )

        draw.ellipse(
            (
                cx - rx2,
                by2 - ry2,
                cx + rx2,
                by2 + ry2
            ),
            fill=blend(
                BUD_TIP_COLOR,
                BG_COLOR,
                alpha_tip
            )
        )


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

def main():

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT)
    )

    draw = ImageDraw.Draw(image)

    # Center of flower
    cx = WIDTH // 2

    # Flower head near the top
    cy = 40

    while True:

        # -----------------------------------------------
        # Get current minute
        # -----------------------------------------------

        minutes_elapsed = (
            bloom_progress()
        )

        # -----------------------------------------------
        # Clear screen
        # -----------------------------------------------

        draw.rectangle(
            (
                0,
                0,
                WIDTH,
                HEIGHT
            ),
            fill=BG_COLOR
        )

        # -----------------------------------------------
        # Draw orchid
        # -----------------------------------------------

        draw_minutes_flower(
            draw,
            cx,
            cy,
            minutes_elapsed
        )

        # -----------------------------------------------
        # Display minute
        # -----------------------------------------------

        draw.text(
            (
                4,
                HEIGHT - 12
            ),
            f"{int(minutes_elapsed):02d}m",
            fill=TEXT_COLOR
        )

        # -----------------------------------------------
        # Send image to display
        # -----------------------------------------------

        disp.image(image)

        # Update ~15 times per second
        time.sleep(1 / 15)


if __name__ == "__main__":
    main()
