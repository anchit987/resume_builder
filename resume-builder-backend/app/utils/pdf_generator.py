# app/utils/pdf_generator.py

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import uuid
import os

def render_resume_to_pdf(data: dict, output_dir: str) -> str:
    print("[PDF GEN] Starting resume rendering")
    print(f"[PDF GEN] Output directory: {output_dir}")
    print(f"[PDF GEN] Input data keys: {list(data.keys())}")

    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("resume_template.html")
    html_content = template.render(**data)

    print("[PDF GEN] Rendered HTML length:", len(html_content))

    output_path = os.path.join(output_dir, f"resume_{uuid.uuid4().hex}.pdf")
    print(f"[PDF GEN] Writing PDF to path: {output_path}")

    HTML(string=html_content).write_pdf(output_path)
    print("[PDF GEN] PDF generation complete")

    return output_path
