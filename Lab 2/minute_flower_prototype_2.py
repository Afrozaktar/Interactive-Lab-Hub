"""
Orchid Flower Clock - Minute Version

The orchid blooms gradually over 60 minutes.

00:00  -> closed bud
15:00  -> partially bloomed
30:00  -> half bloomed
45:00  -> mostly bloomed
59:59  -> fully bloomed
00:00  -> resets to closed bud

The stem/flower stay straight (no wind sway). Instead, a small
creature perches on the flower and hops to a new spot every minute
(on the minute, following the wall clock):

    AM (00:00 - 11:59:59) -> a butterfly
    PM (12:00 - 23:59:59) -> a firefly

The background shifts with the time of day, same as the hour flower:

     8:00 PM - 4:59:59 AM  -> #222059  (night)
     5:00 AM - 7:59:59 AM  -> #FFF7E0  (sunrise)
     8:00 AM - 5:59:59 PM  -> #D9FDFF  (day)
     6:00 PM - 7:59:59 PM  -> #F79940  (sunset)

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


def day_progress(now=None):
    """Hours elapsed since midnight (0.0 - 24.0), used only to pick the
    sky color -- unrelated to the minute-flower bloom timer below."""

    if now is None:
        now = time.time()

    local = time.localtime(now)

    seconds_today = (
        local.tm_hour * 3600
        + local.tm_min * 60
        + local.tm_sec
    )

    return seconds_today / 3600.0


def get_period(now=None):
    """
    'AM' from 00:00 up to (not including) 12:00.
    'PM' from 12:00 (noon) through 23:59:59.
    """

    if now is None:
        now = time.time()

    local = time.localtime(now)

    return "PM" if local.tm_hour >= 12 else "AM"


# -------------------------------------------------------
# ORCHID COLORS
# -------------------------------------------------------

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

# Butterfly (AM)
BUTTERFLY_WING_COLOR = hsb(28, 85, 95)
BUTTERFLY_WING_EDGE = hsb(15, 90, 45)
BUTTERFLY_BODY_COLOR = hsb(0, 0, 10)

# Firefly (PM)
FIREFLY_BODY_COLOR = hsb(0, 0, 12)
FIREFLY_WING_COLOR = hsb(0, 0, 85)
FIREFLY_GLOW_COLOR = hsb(70, 90, 95)


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
    minute_value,
    sky_color
):
    """
    Draw an orchid based on progress through the hour.

    0.0 = closed
    1.0 = fully open

    The bloom animation is unchanged. The stem no longer sways --
    the flower stays straight up.

    sky_color is the current background color (it changes with
    time of day) so the closed-bud overlay fades against it
    correctly instead of a fixed color.
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

    # No wind sway -- the stem and flower stay straight.
    sway_angle = 0.0

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
    # FLOWER POSITION
    # ---------------------------------------------------

    flower_cx = cx
    flower_cy = cy + STEM_TOP

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
        flower_cx,
        flower_cy,
        sway_angle,
        petal_dist * 0.9,
        cur_w * 0.85,
        cur_h * 1.15
    )

    # ---------------------------------------------------
    # LEFT LARGE PETAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        flower_cx,
        flower_cy,
        math.radians(72) + sway_angle,
        petal_dist,
        cur_w * 1.25,
        cur_h
    )

    # ---------------------------------------------------
    # RIGHT LARGE PETAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        flower_cx,
        flower_cy,
        math.radians(-72) + sway_angle,
        petal_dist,
        cur_w * 1.25,
        cur_h
    )

    # ---------------------------------------------------
    # BOTTOM LEFT SEPAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        flower_cx,
        flower_cy,
        math.radians(150) + sway_angle,
        petal_dist * 0.9,
        cur_w * 0.8,
        cur_h * 0.9
    )

    # ---------------------------------------------------
    # BOTTOM RIGHT SEPAL
    # ---------------------------------------------------

    draw_orchid_petal(
        draw,
        flower_cx,
        flower_cy,
        math.radians(-150) + sway_angle,
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
            sway_angle,
            flower_cx,
            flower_cy + 3 * SCALE,
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
            sway_angle,
            flower_cx,
            flower_cy + 4 * SCALE,
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
                flower_cx - throat_w,
                flower_cy + 2.0 * SCALE - 1 * SCALE,
                flower_cx + throat_w,
                flower_cy + 2.0 * SCALE + throat_h
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

        bud_y = flower_cy - 10 * SCALE

        draw.ellipse(
            (
                flower_cx - rx,
                bud_y - ry,
                flower_cx + rx,
                bud_y + ry
            ),
            fill=blend(
                BUD_COLOR,
                sky_color,
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

        bud_tip_y = flower_cy - 25 * SCALE

        draw.ellipse(
            (
                flower_cx - rx2,
                bud_tip_y - ry2,
                flower_cx + rx2,
                bud_tip_y + ry2
            ),
            fill=blend(
                BUD_TIP_COLOR,
                sky_color,
                alpha_tip
            )
        )


# -------------------------------------------------------
# PERCH POSITIONS
# -------------------------------------------------------
#
# A handful of spots around the bloom (top sepal, the two large
# side petals, the two bottom sepals, and the lip). The creature
# hops to the next one every time the wall-clock minute changes.

PERCH_OFFSETS = [
    (0.0, -0.95),
    (0.75, -0.25),
    (-0.75, -0.25),
    (0.55, 0.55),
    (-0.55, 0.55),
    (0.0, 0.15),
]


def get_perch_position(minute_int, flower_cx, flower_cy):
    """
    Return the (x, y) perch position for the given wall-clock
    minute (0-59). Cycles through PERCH_OFFSETS.
    """

    reach = FLOWER_SIZE * 0.9

    dx, dy = PERCH_OFFSETS[
        minute_int % len(PERCH_OFFSETS)
    ]

    return (
        flower_cx + dx * reach,
        flower_cy + dy * reach
    )


# -------------------------------------------------------
# BUTTERFLY (AM)
# -------------------------------------------------------

def draw_butterfly(draw, x, y, t):
    """
    Draw a small fluttering butterfly at (x, y).
    Wings flap using a sine wave driven by wall-clock time
    so it looks alive even while perched in one spot.
    """

    flap = 0.55 + 0.45 * abs(
        math.sin(t * 5.0)
    )

    wing_w = 9 * SCALE * flap
    wing_h = 7 * SCALE

    # Upper (larger) wings
    for side in (-1, 1):

        wing_cx = x + side * 3 * SCALE

        outer = ellipse_points(
            wing_w,
            wing_h,
            math.radians(side * -25),
            wing_cx,
            y - 3 * SCALE,
            n=14
        )

        draw.polygon(outer, fill=BUTTERFLY_WING_EDGE)

        inner = ellipse_points(
            wing_w * 0.8,
            wing_h * 0.78,
            math.radians(side * -25),
            wing_cx,
            y - 3 * SCALE,
            n=14
        )

        draw.polygon(inner, fill=BUTTERFLY_WING_COLOR)

    # Lower (smaller) wings
    for side in (-1, 1):

        wing_cx = x + side * 2.2 * SCALE

        outer = ellipse_points(
            wing_w * 0.6,
            wing_h * 0.55,
            math.radians(side * 20),
            wing_cx,
            y + 2 * SCALE,
            n=12
        )

        draw.polygon(outer, fill=BUTTERFLY_WING_EDGE)

        inner = ellipse_points(
            wing_w * 0.48,
            wing_h * 0.44,
            math.radians(side * 20),
            wing_cx,
            y + 2 * SCALE,
            n=12
        )

        draw.polygon(inner, fill=BUTTERFLY_WING_COLOR)

    # Body
    body_r = 1.6 * SCALE

    draw.ellipse(
        (
            x - body_r,
            y - 4 * SCALE,
            x + body_r,
            y + 4 * SCALE
        ),
        fill=BUTTERFLY_BODY_COLOR
    )

    # Antennae
    draw.line(
        (x - 1 * SCALE, y - 4 * SCALE, x - 3 * SCALE, y - 7 * SCALE),
        fill=BUTTERFLY_BODY_COLOR,
        width=1
    )

    draw.line(
        (x + 1 * SCALE, y - 4 * SCALE, x + 3 * SCALE, y - 7 * SCALE),
        fill=BUTTERFLY_BODY_COLOR,
        width=1
    )


# -------------------------------------------------------
# FIREFLY (PM)
# -------------------------------------------------------

def draw_firefly(draw, x, y, t, sky_color):
    """
    Draw a small firefly at (x, y) with a softly pulsing glow
    at its tail. Blended against sky_color since a plain RGB
    image can't do real alpha transparency.
    """

    pulse = 0.5 + 0.5 * math.sin(t * 3.0)

    body_len = 6 * SCALE
    body_w = 2 * SCALE

    tail_x = x
    tail_y = y + body_len / 2

    # Soft outer halo
    halo_r = 2.2 * SCALE * (1.5 + pulse * 0.7)
    halo_alpha = 15 + pulse * 25

    draw.ellipse(
        (
            tail_x - halo_r,
            tail_y - halo_r,
            tail_x + halo_r,
            tail_y + halo_r
        ),
        fill=blend(FIREFLY_GLOW_COLOR, sky_color, halo_alpha)
    )

    # Wings
    for side in (-1, 1):

        wing_cx = x + side * 2 * SCALE

        pts = ellipse_points(
            4 * SCALE,
            2.2 * SCALE,
            math.radians(side * -15),
            wing_cx,
            y - 1 * SCALE,
            n=10
        )

        draw.polygon(
            pts,
            fill=blend(FIREFLY_WING_COLOR, sky_color, 55)
        )

    # Body
    draw.ellipse(
        (
            x - body_w,
            y - body_len / 2,
            x + body_w,
            y + body_len / 2
        ),
        fill=FIREFLY_BODY_COLOR
    )

    # Bright glowing tail tip, drawn last so it's on top
    glow_r = 1.8 * SCALE
    glow_alpha = 55 + pulse * 45

    draw.ellipse(
        (
            tail_x - glow_r,
            tail_y - glow_r,
            tail_x + glow_r,
            tail_y + glow_r
        ),
        fill=blend(FIREFLY_GLOW_COLOR, sky_color, glow_alpha)
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
        # Get current minute / time-of-day info
        # -----------------------------------------------

        minutes_elapsed = (
            bloom_progress()
        )

        now = time.time()
        local = time.localtime(now)

        sky_color = get_sky_color(
            day_progress(now)
        )

        period = get_period(now)

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
            fill=sky_color
        )

        # -----------------------------------------------
        # Draw orchid (stays straight, no sway)
        # -----------------------------------------------

        draw_minutes_flower(
            draw,
            cx,
            cy,
            minutes_elapsed,
            sky_color
        )

        # -----------------------------------------------
        # Draw the perched creature -- hops to a new spot
        # every wall-clock minute; butterfly before noon,
        # firefly from noon onward.
        # -----------------------------------------------

        flower_cx = cx
        flower_cy = cy + STEM_TOP

        perch_x, perch_y = get_perch_position(
            local.tm_min,
            flower_cx,
            flower_cy
        )

        if period == "AM":
            draw_butterfly(draw, perch_x, perch_y, now)
        else:
            draw_firefly(draw, perch_x, perch_y, now, sky_color)

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
