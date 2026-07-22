from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"

BG = "#f7fafc"
TEXT = "#102a43"
BLUE = "#1363df"
TEAL = "#0f8b8d"
YELLOW = "#f4b942"
LINE = "#829ab1"
WHITE = "#ffffff"


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    selected_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str = TEXT,
) -> None:
    left, top, right, bottom = box
    bounds = draw.multiline_textbbox((0, 0), text, font=selected_font, align="center")
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    draw.multiline_text(
        ((left + right - width) / 2, (top + bottom - height) / 2),
        text,
        font=selected_font,
        fill=fill,
        align="center",
    )


def main() -> None:
    image = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(image)
    draw.text((60, 45), "Provable Agent Reference Framework", font=font(34, bold=True), fill=TEXT)
    boxes = [
        ((70, 300, 310, 490), "Agent\nsemantic draft", BLUE),
        ((380, 300, 640, 490), "Trusted\ncompiler", TEAL),
        ((710, 300, 970, 490), "Deterministic\nverification", TEAL),
        ((1040, 210, 1280, 390), "Human\napproval", YELLOW),
        ((1040, 500, 1280, 680), "Exact-use\nauthorization", YELLOW),
        ((1350, 355, 1550, 535), "Authorized\noutput", BLUE),
    ]
    for box, label, color in boxes:
        draw.rounded_rectangle(box, radius=24, fill=WHITE, outline=color, width=5)
        centered(draw, box, label, font(28, bold=True), color)
    centers = [(310, 395, 380, 395), (640, 395, 710, 395), (970, 350, 1040, 300), (1160, 390, 1160, 500), (1280, 590, 1350, 445)]
    for x1, y1, x2, y2 in centers:
        draw.line((x1, y1, x2, y2), fill=LINE, width=5)
    OUT.mkdir(exist_ok=True)
    image.save(OUT / "agent-interactions.png", optimize=True)

    sequence = Image.new("RGB", (1600, 950), BG)
    draw = ImageDraw.Draw(sequence)
    draw.text((60, 40), "Provable-agent control sequence", font=font(34, bold=True), fill=TEXT)
    names = ["Agent", "Compiler", "Verifier", "Human", "Authorizer", "Audit"]
    positions = [130, 390, 650, 910, 1170, 1430]
    for position, name in zip(positions, names, strict=True):
        draw.rounded_rectangle(
            (position - 90, 120, position + 90, 190),
            radius=20,
            fill=WHITE,
            outline=BLUE if name == "Agent" else TEAL,
            width=4,
        )
        centered(draw, (position - 90, 120, position + 90, 190), name, font(25, bold=True))
        draw.line((position, 190, position, 880), fill=LINE, width=2)
    OUT.mkdir(exist_ok=True)
    sequence.save(OUT / "agent-sequence.png", optimize=True)


if __name__ == "__main__":
    main()
