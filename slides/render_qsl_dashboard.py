"""Render the frozen QSL scores as a dashboard-style vector heatmap."""

import json
from pathlib import Path


ASSETS = Path(__file__).resolve().parent / "assets/2026-09-16-200514"
data = json.loads((ASSETS / "qsl-data.json").read_text())
matrix = data["matrix"]
rows, columns = len(matrix), len(matrix[0])
pitch, gap, margin = 10, 1.1, 8
width, height = columns * pitch + 2 * margin, rows * pitch + 60
commands = [f"1 1 1 rg 0 0 {width} {height} re f"]


def colour(value):
    if value is None:
        return (0.80, 0.81, 0.82)
    t = min(1, max(0, value)) ** 0.65
    low, high = (229, 241, 243), (18, 126, 134)
    return tuple((a + t * (b - a)) / 255 for a, b in zip(low, high))


def rounded_cell(x, y, size, radius=1.6):
    k = radius * 0.55228475
    r = radius
    return (
        f"{x+r} {y} m {x+size-r} {y} l "
        f"{x+size-r+k} {y} {x+size} {y+r-k} {x+size} {y+r} c "
        f"{x+size} {y+size-r} l "
        f"{x+size} {y+size-r+k} {x+size-r+k} {y+size} {x+size-r} {y+size} c "
        f"{x+r} {y+size} l "
        f"{x+r-k} {y+size} {x} {y+size-r+k} {x} {y+size-r} c "
        f"{x} {y+r} l {x} {y+r-k} {x+r-k} {y} {x+r} {y} c h f"
    )


for i, row in enumerate(matrix):
    for j, value in enumerate(row):
        rgb = colour(value)
        commands.append(" ".join(f"{c:.4f}" for c in rgb) + " rg")
        commands.append(rounded_cell(
            margin + j * pitch, margin + (rows - i - 1) * pitch, pitch - gap
        ))

for step in range(160):
    rgb = colour(step / 159)
    commands.append(" ".join(f"{c:.4f}" for c in rgb) + " rg")
    commands.append(f"{margin + step} {height - 30} 1.1 13 re f")
commands.append(
    f"0.36 0.41 0.47 rg BT /F1 17 Tf {margin + 175} {height - 29} Td "
    "(Low to high scan score) Tj ET"
)
stream = "\n".join(commands).encode("ascii")
objects = [
    b"<< /Type /Catalog /Pages 2 0 R >>",
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
     "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>").encode(),
    f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
]
output = bytearray(b"%PDF-1.4\n")
offsets = [0]
for number, obj in enumerate(objects, 1):
    offsets.append(len(output))
    output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
xref = len(output)
output.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
for offset in offsets[1:]:
    output.extend(f"{offset:010d} 00000 n \n".encode())
output.extend(
    f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
)
(ASSETS / "qsl-dashboard.pdf").write_bytes(output)
