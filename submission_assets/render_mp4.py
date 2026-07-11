import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

# Frame settings
W, H = 1280, 720
FPS = 1  # 1 frame per second for static slides
DURATIONS = [5, 8, 8, 12, 8, 5]  # seconds per frame
TOTAL_DURATION = sum(DURATIONS)  # 46 seconds

BG_COLOR = (15, 15, 25)
TEXT_COLOR = (240, 240, 240)
ACCENT_COLOR = (237, 28, 36)  # AMD red
CODE_BG = (30, 30, 45)

def get_font(size):
    # Try common monospace fonts, fallback to default
    for name in ["Consolas", "Courier New", "DejaVu Sans Mono", "Liberation Mono"]:
        try:
            return ImageFont.truetype(name, size)
        except:
            pass
    return ImageFont.load_default()

def get_font_bold(size):
    for name in ["Consolas Bold", "Courier New Bold", "DejaVu Sans Mono Bold"]:
        try:
            return ImageFont.truetype(name, size)
        except:
            pass
    return get_font(size)

def draw_frame(title, lines, subtitle=""):
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Title bar
    draw.rectangle([0, 0, W, 60], fill=(25, 25, 40))
    font_title = get_font_bold(28)
    draw.text((30, 15), title, fill=ACCENT_COLOR, font=font_title)
    
    if subtitle:
        font_sub = get_font(14)
        draw.text((30, 42), subtitle, fill=(150, 150, 150), font=font_sub)
    
    # Content area
    y = 80
    font_line = get_font(18)
    font_code = get_font(16)
    
    for line in lines:
        if line.startswith("```"):
            y += 5
        elif line.startswith("  ") or line.startswith("    "):
            # Code/indented block
            draw.rectangle([40, y, W - 40, y + 24], fill=CODE_BG)
            draw.text((50, y + 2), line.strip(), fill=(200, 200, 200), font=font_code)
            y += 26
        elif line.startswith("-"):
            draw.text((50, y), line, fill=TEXT_COLOR, font=font_line)
            y += 28
        elif line.startswith("http") or line.startswith("ghcr"):
            draw.text((50, y), line, fill=(100, 200, 255), font=font_code)
            y += 28
        elif line == "":
            y += 10
        else:
            draw.text((50, y), line, fill=TEXT_COLOR, font=font_line)
            y += 28
    
    return img

frames = [
    (
        "AMD Track 1 Submission",
        [
            "",
            "Local-First Token Router",
            "",
            "A Dockerized benchmark agent for",
            "AMD Developer Hackathon Act II - Track 1",
            "",
            "Image: ghcr.io/itz1508/amd-track1:latest",
            "Platform: linux/amd64  |  Size: ~46 MB",
        ],
        "Public GHCR Container Demo"
    ),
    (
        "Step 1: Public GHCR Package",
        [
            "",
            "GitHub Container Registry:",
            "",
            "  https://github.com/users/itz1508",
            "  /packages/container/amd-track1",
            "",
            "Visibility: PUBLIC",
            "Anonymous pull: VERIFIED",
        ],
        "Package page shows public access badge"
    ),
    (
        "Step 2: Anonymous Pull + Digest",
        [
            "",
            "$ docker logout ghcr.io",
            "$ docker pull ghcr.io/itz1508/amd-track1:latest",
            "",
            "$ docker inspect --format='{{index .RepoDigests 0}}'",
            "  ghcr.io/itz1508/amd-track1:latest",
            "",
            "ghcr.io/itz1508/amd-track1@sha256:",
            "330144fa6ed285a5087757d8ba2710d7ae8cb04ed044c07c7f7548bcb80a7083",
        ],
        "Digest matches immutable reference"
    ),
    (
        "Step 3: Docker Run",
        [
            "",
            "$ mkdir demo-input demo-output",
            "$ echo '[{\"task_id\":\"demo-1\",...' > demo-input/tasks.json",
            "",
            "$ docker run --rm \\",
            "    -v \"${PWD}/demo-input:/input:ro\" \\",
            "    -v \"${PWD}/demo-output:/output\" \\",
            "    -e AMD_REMOTE_MODE=off \\",
            "    -e FIREWORKS_API_KEY=placeholder \\",
            "    ghcr.io/itz1508/amd-track1:latest",
        ],
        "Deterministic task needs no external model"
    ),
    (
        "Step 4: Output Verification",
        [
            "",
            "$ cat demo-output/results.json",
            "",
            "[",
            '  {"task_id": "demo-1", "answer": "4"}',
            "]",
            "",
            "Contract satisfied:",
            "- /input/tasks.json  ->  /output/results.json",
        ],
        "Valid JSON with exact task_id and answer fields"
    ),
    (
        "Submission Ready",
        [
            "",
            "Image:",
            "  ghcr.io/itz1508/amd-track1:latest",
            "",
            "Digest:",
            "  sha256:330144fa6ed285a5087757d8ba2710d7",
            "  ae8cb04ed044c07c7f7548bcb80a7083",
            "",
            "Status: Public  |  linux/amd64  |  No secrets",
        ],
        "Ready for AMD Track 1 submission form"
    ),
]

# Generate frames
os.makedirs("submission_assets/frames", exist_ok=True)
frame_files = []

for i, (title, lines, subtitle) in enumerate(frames):
    img = draw_frame(title, lines, subtitle)
    # Duplicate frame for duration
    for j in range(DURATIONS[i]):
        path = f"submission_assets/frames/frame_{i:02d}_{j:02d}.png"
        img.save(path)
        frame_files.append(path)

# Build ffmpeg concat list
concat_path = "submission_assets/frames/concat.txt"
with open(concat_path, "w") as f:
    for fp in frame_files:
        f.write(f"file '{os.path.abspath(fp)}'\n")
        f.write(f"duration 1\n")
    # Last frame needs explicit duration for concat demuxer
    if frame_files:
        f.write(f"file '{os.path.abspath(frame_files[-1])}'\n")

# Render MP4
mp4_path = "submission_assets/amd-track1-demo.mp4"
cmd = [
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", concat_path,
    "-vsync", "vfr",
    "-pix_fmt", "yuv420p",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "23",
    "-movflags", "+faststart",
    mp4_path,
]

print(f"Rendering {len(frame_files)} frames -> {mp4_path}")
print(f"Total duration: {TOTAL_DURATION}s")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("FFmpeg stderr:", result.stderr[-500:])
    raise RuntimeError("ffmpeg failed")
print(f"MP4 generated: {mp4_path}")

# Cleanup frames
for fp in frame_files:
    os.remove(fp)
os.remove(concat_path)
os.rmdir("submission_assets/frames")
print("Cleaned up temporary frames")