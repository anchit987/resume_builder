import os
import subprocess
import logging
from jinja2 import Environment, FileSystemLoader

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

TEMPLATE_PATH = r"C://Users//HP//Desktop//resumebuilder//resume_builder//resume-builder-backend//app//templates"

LATEX_ESCAPE = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
}

LINK_KEYS = {"website", "linkedin", "github"}

def escape_latex(text):
    if not text or not isinstance(text, str):
        return text
    for char, replacement in LATEX_ESCAPE.items():
        text = text.replace(char, replacement)
    return text

def preprocess_resume_data(data, parent_key=None):
    """Recursively escape LaTeX characters except URLs."""
    if isinstance(data, dict):
        return {k: preprocess_resume_data(v, k) for k, v in data.items()}
    elif isinstance(data, list):
        return [preprocess_resume_data(v, parent_key) for v in data]
    elif isinstance(data, str):
        if parent_key in LINK_KEYS:
            return data  # don't escape URLs
        return escape_latex(data)
    return data


def generate_latex_from_resume(resume_data):
    logging.info("Preprocessing resume data for LaTeX...")
    resume_data = preprocess_resume_data(resume_data)

    logging.info(f"Loading Jinja2 environment from: {TEMPLATE_PATH}")
    env = Environment(loader=FileSystemLoader(TEMPLATE_PATH))

    template_name = "resume_template.tex.j2"
    logging.info(f"Loading LaTeX template: {template_name}")
    template = env.get_template(template_name)

    logging.info("Rendering LaTeX content...")
    return template.render(**resume_data)

def render_resume_to_pdf(resume_data, output_dir, return_log=False):
    logging.info("Starting PDF generation...")

    tex_content = generate_latex_from_resume(resume_data)

    tex_file = os.path.join(output_dir, "resume.tex")
    pdf_file = os.path.join(output_dir, "resume.pdf")
    log_file = os.path.join(output_dir, "pdflatex.log")

    logging.info(f"Writing LaTeX to: {tex_file}")
    with open(tex_file, "w", encoding="utf-8") as f:
        f.write(tex_content)

    logging.info(f"Running pdflatex in: {output_dir}")
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "resume.tex"],
        cwd=output_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    logging.info("Saving pdflatex logs...")
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(result.stdout + "\n" + result.stderr)

    if result.returncode != 0:
        logging.error("PDF generation failed! Check pdflatex.log for details.")

    logging.info(f"PDF generation {'succeeded' if result.returncode == 0 else 'failed'}: {pdf_file}")

    if return_log:
        return pdf_file, result.stdout + result.stderr
    return pdf_file
