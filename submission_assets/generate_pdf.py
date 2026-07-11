from fpdf import FPDF

class SlidePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

pdf = SlidePDF()
pdf.set_auto_page_break(auto=False)

slides = [
    (
        "AMD Track 1 Local-First Token Router",
        "A Dockerized benchmark agent for AMD Developer Hackathon Act II Track 1."
    ),
    (
        "Problem",
        "Track 1 ranks submissions by lowest recorded Fireworks token usage after passing the accuracy gate.\n\n"
        "The agent must:\n"
        "  - Stay compliant with the contest contract\n"
        "  - Read /input/tasks.json\n"
        "  - Write valid /output/results.json\n"
        "  - Minimize remote token consumption"
    ),
    (
        "Solution",
        "Deterministic-first + Fireworks rescue architecture\n\n"
        "  - Local deterministic tools when correctness is provable\n"
        "  - Input validation and output verification before acceptance\n"
        "  - Fireworks AI rescue only when model inference is required\n"
        "  - Remote calls routed exclusively through FIREWORKS_BASE_URL\n"
        "  - Model selection restricted to ALLOWED_MODELS at runtime"
    ),
    (
        "Submission Artifact",
        "Image:\n"
        "  ghcr.io/itz1508/amd-track1:latest\n\n"
        "Digest:\n"
        "  ghcr.io/itz1508/amd-track1@sha256:330144fa6ed285a5087757d8ba2710d7ae8cb04ed044c07c7f7548bcb80a7083\n\n"
        "Status:\n"
        "  - linux/amd64\n"
        "  - Public GHCR pull verified\n"
        "  - Minimized image (~46 MB)\n"
        "  - No bundled secrets\n"
        "  - Valid /input -> /output smoke test passed"
    ),
]

for title, body in slides:
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 20, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 10, body)

output_path = "submission_assets/AMD_Track1_Slides.pdf"
pdf.output(output_path)
print(f"PDF generated: {output_path}")