#!/usr/bin/env python3
"""
flower_clock_hours.py

Sunflower Hour Flower from Lamiah Khan's "Flower Clock"

The sunflower has 12 petals representing a 12-hour half-day cycle.
The flower is in full bloom (all 12 petals) at 00:00 (midnight)
and again at 12:00:00 (noon).

00:00  -> 12 petals (full bloom)
01:00  -> first petal falls
02:00  -> second petal falls
...
11:00  -> 11th petal falls
12:00  -> resets to 12 petals (full bloom)
13:00  -> first petal falls again
...
23:00  -> 11th petal falls
00:00  -> resets to 12 petals (full bloom)

Each petal falls smoothly during its corresponding hour.
Once a petal reaches the bottom of the screen, it stays there
for the remainder of that 12-hour half.

The flower itself remains a sunflower with:
- 12 narrow, pointed yellow-orange petals
- Large dark brown disc center
- Fibonacci/Vogel seed pattern
- Broad dark-green leaves
- Sky-colored background that shifts with time of day
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
    """Blend fg over bg."""

    a = max(0.0, min(1.0, alpha_pct / 100.0))

    return tuple(
        round(fg[i] * a + bg[i] * (1 - a))
        for i in range(3)
    )


def hex_to_rgb(hex_str):
    """Convert a '#RRGGBB' string to an (r, g, b) tuple."""

    hex_str = hex_str.lstrip("#")

    return tuple(
        int(hex_str[i:i + 2], 16)
        for i in (0, 2, 4)
    )


# -------------------------------------------------------
# SKY / BACKGROUND COLORS
# -------------------------------------------------------
#
#  8:00 PM - 4:59:59 AM  -> #222059  (night)
#  5:00 AM - 7:59:59 AM  -> #FFF7E0  (sunrise)
#  8:00 AM - 5:59:59 PM  -> #D9FDFF  (day)
#  6:00 PM - 7:59:59 PM  -> #F79940  (sunset)

NIGHT_SKY_COLOR    = hex_to_rgb("#222059")
SUNRISE_SKY_COLOR  = hex_to_rgb("#FFF7E0")
DAY_SKY_COLOR      = hex_to_rgb("#D9FDFF")
SUNSET_SKY_COLOR   = hex_to_rgb("#F79940")


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


# -------------------------------------------------------
# SUNFLOWER COLORS
# -------------------------------------------------------

# Stem and leaves
STEM_COLOR = hsb(100, 55, 40)
LEAF_COLOR = hsb(100, 70, 40)
LEAF_STROKE = hsb(100, 80, 22)

# Sunflower center
CENTER_COLOR = hsb(30, 65, 35)
CENTER_EDGE_COLOR = hsb(35, 75, 55)
SEED_COLOR = hsb(25, 75, 18)

# Sunflower petals
PETAL_FILL = hsb(46, 90, 98)
PETAL_STROKE = hsb(38, 95, 65)
PETAL_HIGHLIGHT = hsb(52, 45, 100)

# Fallen petals
FALLEN_PETAL_COLOR = PETAL_FILL
FALLEN_PETAL_STROKE = PETAL_STROKE

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


def marquise_points(
    base_dist,
    length,
    width,
    angle,
    ox,
    oy,
    n=10
):
    """
    Create a pointed almond/marquise shape.
    Used for sunflower petals and leaves.
    """

    pts = []

    for i in range(n + 1):

        t = i / n

        lx = (
            width / 2
            * math.sin(math.pi * t)
        )

        ly = -(
            base_dist
            + length * t
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

    for i in range(n + 1):

        t = 1 - i / n

        lx = -(
            width / 2
            * math.sin(math.pi * t)
        )

        ly = -(
            base_dist
            + length * t
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

# 12 petals: full bloom at midnight (0:00) and noon (12:00),
# one petal falls per hour through each 12-hour half of the day.
PETAL_COUNT = 12

GOLDEN_ANGLE = (
    math.pi
    * (3 - math.sqrt(5))
)


# -------------------------------------------------------
# TIME
# -------------------------------------------------------

def day_progress(now=None):
    """
    Return hours elapsed since midnight.

    00:00 -> 0.0
    06:30 -> 6.5
    12:00 -> 12.0
    23:59 -> ~24.0
    """

    if now is None:
        now = time.time()

    local = time.localtime(now)

    seconds_today = (
        local.tm_hour * 3600
        + local.tm_min * 60
        + local.tm_sec
    )

    return seconds_today / 3600.0


def half_day_progress(hour_value):
    """
    Return hours elapsed since the most recent 12-hour mark
    (midnight or noon).

    00:00 -> 0.0
    06:30 -> 6.5
    12:00 -> 0.0  (resets - full bloom)
    18:30 -> 6.5
    23:59 -> ~11.99
    """

    return hour_value % 12


# -------------------------------------------------------
# LEAVES
# -------------------------------------------------------

def draw_leaves(
    draw,
    cx,
    cy,
    hour_value
):
    """
    Draw sunflower leaves.

    Leaves gradually appear throughout the day,
    maintaining the original hour-flower theme.
    """

    num_leaves = (
        int(hour_value // 3)
        + 2
    )

    num_leaves = min(
        num_leaves,
        9
    )

    for i in range(num_leaves):

        leaf_y = (
            78 * SCALE
            + i * (16 * SCALE)
        )

        side = (
            -1
            if i % 2 == 0
            else 1
        )

        anchor_x = (
            cx
            + side * (4 * SCALE)
        )

        anchor_y = (
            cy
            + leaf_y
        )

        leaf_angle = (
            side
            * (0.85 + i * 0.06)
        )

        leaf_len = (
            (30 + i * 3)
            * SCALE
        )

        leaf_w = (
            (22 + i * 2)
            * SCALE
        )

        # Dark outline
        stroke_pts = marquise_points(
            0,
            leaf_len * 1.06,
            leaf_w * 1.15,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        draw.polygon(
            stroke_pts,
            fill=LEAF_STROKE
        )

        # Main leaf
        fill_pts = marquise_points(
            0,
            leaf_len,
            leaf_w,
            leaf_angle,
            anchor_x,
            anchor_y
        )

        draw.polygon(
            fill_pts,
            fill=LEAF_COLOR
        )


# -------------------------------------------------------
# SUNFLOWER PETAL
# -------------------------------------------------------

def draw_petal(
    draw,
    cx,
    cy,
    angle,
    petal_dist,
    cur_w,
    cur_h
):
    """
    Draw one sunflower ray petal.
    """

    # Dark outline
    stroke_pts = marquise_points(
        petal_dist - cur_h * 0.04,
        cur_h * 1.08,
        cur_w * 1.15,
        angle,
        cx,
        cy
    )

    draw.polygon(
        stroke_pts,
        fill=PETAL_STROKE
    )

    # Yellow-orange fill
    fill_pts = marquise_points(
        petal_dist,
        cur_h,
        cur_w,
        angle,
        cx,
        cy
    )

    draw.polygon(
        fill_pts,
        fill=PETAL_FILL
    )

    # Highlight
    hi_pts = marquise_points(
        petal_dist + cur_h * 0.05,
        cur_h * 0.45,
        cur_w * 0.35,
        angle,
        cx,
        cy
    )

    draw.polygon(
        hi_pts,
        fill=PETAL_HIGHLIGHT
    )


# -------------------------------------------------------
# FALLEN PETAL
# -------------------------------------------------------

def draw_fallen_petal(
    draw,
    x,
    y,
    angle,
    size
):
    """
    Draw a petal that has fallen to the bottom.

    The petal is smaller than the flower petal and
    rotated slightly so the fallen petals don't look
    perfectly identical.
    """

    width = 9 * SCALE * size
    height = 25 * SCALE * size

    pts = marquise_points(
        0,
        height,
        width,
        angle,
        x,
        y
    )

    draw.polygon(
        pts,
        fill=FALLEN_PETAL_STROKE
    )

    pts_inner = marquise_points(
        0,
        height * 0.92,
        width * 0.82,
        angle,
        x,
        y
    )

    draw.polygon(
        pts_inner,
        fill=FALLEN_PETAL_COLOR
    )


# -------------------------------------------------------
# SUNFLOWER CENTER
# -------------------------------------------------------

def draw_center(
    draw,
    cx,
    cy,
    center_r
):
    """
    Draw the sunflower center with Fibonacci seed packing.
    """

    # Outer edge
    draw.ellipse(
        (
            cx - center_r,
            cy - center_r,
            cx + center_r,
            cy + center_r
        ),
        fill=CENTER_EDGE_COLOR
    )

    # Inner disc
    inner_r = (
        center_r * 0.9
    )

    draw.ellipse(
        (
            cx - inner_r,
            cy - inner_r,
            cx + inner_r,
            cy + inner_r
        ),
        fill=CENTER_COLOR
    )

    # Seeds
    num_seeds = 55

    seed_r = max(
        0.5,
        center_r * 0.11
    )

    for i in range(num_seeds):

        frac = (
            i
            / max(1, num_seeds - 1)
        )

        r = (
            inner_r
            * 0.92
            * math.sqrt(frac)
        )

        theta = (
            i
            * GOLDEN_ANGLE
        )

        sx = (
            cx
            + r * math.cos(theta)
        )

        sy = (
            cy
            + r * math.sin(theta)
        )

        draw.ellipse(
            (
                sx - seed_r,
                sy - seed_r,
                sx + seed_r,
                sy + seed_r
            ),
            fill=SEED_COLOR
        )


# -------------------------------------------------------
# FLOWER
# -------------------------------------------------------

def draw_hours_flower(
    draw,
    cx,
    cy,
    hour_value
):
    """
    Draw the sunflower.

    12 petals are attached to the flower at midnight and
    again at noon (hour_value should already be the
    hours-since-last-12-hour-mark value, i.e. 0.0 - 12.0).

    At each hour within the current 12-hour half:
        one additional petal is considered fallen.

    During the current hour, that petal moves smoothly
    from the flower toward the bottom of the screen.
    """

    # ---------------------------------------------------
    # FLOWER SIZE
    # ---------------------------------------------------

    base_radius = (
        FLOWER_SIZE * 0.32
    )

    bloom_radius = (
        FLOWER_SIZE * 0.64
    )

    petal_w = (
        17 * SCALE
    )

    petal_h = (
        80 * SCALE
    )

    petal_dist = (
        base_radius
    )

    cur_w = petal_w
    cur_h = petal_h

    # ---------------------------------------------------
    # DETERMINE FALLEN PETALS
    # ---------------------------------------------------

    completed_hours = int(
        hour_value
    )

    # Current hour's falling progress.
    hour_fraction = (
        hour_value
        - completed_hours
    )

    # ---------------------------------------------------
    # DRAW REMAINING PETALS
    # ---------------------------------------------------

    for i in range(PETAL_COUNT):

        # Petal i falls during hour i.
        if i < completed_hours:
            continue

        angle = (
            2
            * math.pi
            * i
            / PETAL_COUNT
        )

        draw_petal(
            draw,
            cx,
            cy,
            angle,
            petal_dist,
            cur_w,
            cur_h
        )

    # ---------------------------------------------------
    # CURRENT FALLING PETAL
    # ---------------------------------------------------

    if completed_hours < PETAL_COUNT:

        falling_index = (
            completed_hours
        )

        falling_angle = (
            2
            * math.pi
            * falling_index
            / PETAL_COUNT
        )

        # ------------------------------------------------
        # PETAL START POSITION
        # ------------------------------------------------

        start_x, start_y = transform(
            0,
            -(
                petal_dist
                + cur_h * 0.75
            ),
            falling_angle,
            cx,
            cy
        )

        # ------------------------------------------------
        # BOTTOM TARGET
        # ------------------------------------------------

        # Spread fallen petals along the bottom so
        # they accumulate instead of overlapping.
        spacing = WIDTH / (
            PETAL_COUNT + 1
        )

        target_x = (
            spacing
            * (falling_index + 1)
        )

        target_y = (
            HEIGHT - 7
        )

        # ------------------------------------------------
        # FALL MOTION
        # ------------------------------------------------

        # Smooth ease-in/ease-out movement.
        t = hour_fraction

        t_smooth = (
            t * t * (3 - 2 * t)
        )

        falling_x = (
            start_x
            + (
                target_x
                - start_x
            )
            * t_smooth
        )

        falling_y = (
            start_y
            + (
                target_y
                - start_y
            )
            * t_smooth
        )

        # Give each falling petal a little rotation.
        falling_rotation = (
            falling_angle
            + t * math.pi * 1.5
        )

        # Slightly larger while falling.
        draw_fallen_petal(
            draw,
            falling_x,
            falling_y,
            falling_rotation,
            1.0
        )

    # ---------------------------------------------------
    # DRAW PETALS THAT HAVE ALREADY FALLEN
    # ---------------------------------------------------

    for i in range(
        completed_hours
    ):

        spacing = WIDTH / (
            PETAL_COUNT + 1
        )

        fallen_x = (
            spacing
            * (i + 1)
        )

        fallen_y = (
            HEIGHT - 7
        )

        fallen_rotation = (
            -0.45
            + (
                i % 5
                * 0.22
            )
        )

        draw_fallen_petal(
            draw,
            fallen_x,
            fallen_y,
            fallen_rotation,
            1.0
        )

    # ---------------------------------------------------
    # CENTER
    # ---------------------------------------------------

    center_r = (
        20 * SCALE
    )

    draw_center(
        draw,
        cx,
        cy,
        center_r
    )


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

def main():

    image = Image.new(
        "RGB",
        (WIDTH, HEIGHT)
    )

    draw = ImageDraw.Draw(
        image
    )

    # Center of flower
    cx = WIDTH // 2

    # Flower head near top
    cy = 40

    while True:

        # -----------------------------------------------
        # CURRENT TIME
        # -----------------------------------------------

        hours_elapsed = (
            day_progress()
        )

        # Petals follow a 12-hour cycle: full bloom at
        # midnight and noon.
        petal_hour_value = (
            half_day_progress(hours_elapsed)
        )

        local = time.localtime()

        # -----------------------------------------------
        # CLEAR SCREEN (sky color based on time of day)
        # -----------------------------------------------

        draw.rectangle(
            (
                0,
                0,
                WIDTH,
                HEIGHT
            ),
            fill=get_sky_color(hours_elapsed)
        )

        # -----------------------------------------------
        # DRAW SUNFLOWER
        # -----------------------------------------------

        draw_hours_flower(
            draw,
            cx,
            cy,
            petal_hour_value
        )

        # -----------------------------------------------
        # DRAW STEM
        # -----------------------------------------------

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
                round(9 * SCALE)
            )
        )

        # -----------------------------------------------
        # DRAW LEAVES
        # -----------------------------------------------

        draw_leaves(
            draw,
            cx,
            cy,
            hours_elapsed
        )

        # -----------------------------------------------
        # TIME DISPLAY
        # -----------------------------------------------

        draw.text(
            (
                4,
                HEIGHT - 22
            ),
            time.strftime(
                "%H:%M:%S",
                local
            ),
            fill=TEXT_COLOR
        )

        # Number of petals remaining (in the current
        # 12-hour half)
        petals_remaining = max(
            0,
            PETAL_COUNT
            - int(petal_hour_value)
        )

        draw.text(
            (
                4,
                HEIGHT - 12
            ),
            f"{petals_remaining} petals",
            fill=TEXT_COLOR
        )

        # -----------------------------------------------
        # SEND TO DISPLAY
        # -----------------------------------------------

        disp.image(image)

        # Keep animation smooth.
        time.sleep(
            1 / 15
        )


if __name__ == "__main__":
    main()
