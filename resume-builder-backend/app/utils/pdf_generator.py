import os
import re
import subprocess
import logging
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EnhancedPDFGenerator:
    """Enhanced PDF generator with proper LaTeX escaping to avoid broken % signs."""
    
    def __init__(self, template_path: str = None):
        self.template_path = template_path or r"C://Users//HP//Desktop//resumebuilder//resume_builder//resume-builder-backend//app//templates"
        
        self.latex_escape = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\^{}',
            '\\': r'\textbackslash{}'
        }
        
        self.no_escape_keys = {"website", "linkedin", "github", "portfolio", "link"}
    
    def escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters exactly once."""
        if not text or not isinstance(text, str):
            return text

        # Normalize fancy characters
        text = (
            text.replace("–", "--")  # En dash
                .replace("—", "---")  # Em dash
                .replace("’", "'")
                .replace("‘", "'")
                .replace("“", '"')
                .replace("”", '"')
        )

        # Use regex to escape special chars without double escaping
        pattern = re.compile('|'.join(re.escape(c) for c in self.latex_escape))
        return pattern.sub(lambda m: self.latex_escape[m.group()], text)

    def preprocess_resume_data(self, data, parent_key=None):
        """Recursively escape LaTeX characters with improved handling."""
        if isinstance(data, dict):
            return {k: self.preprocess_resume_data(v, k) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.preprocess_resume_data(v, parent_key) for v in data]
        elif isinstance(data, str):
            if parent_key in self.no_escape_keys or self._is_url(data):
                return data
            return self.escape_latex(data)
        return data
    
    def _is_url(self, text: str) -> bool:
        return isinstance(text, str) and text.lower().startswith(('http://', 'https://', 'www.', 'mailto:'))

    def validate_resume_data(self, resume_data: Dict) -> Dict:
        """Validate and normalize resume data."""
        cleaned_data = {}
        cleaned_data['name'] = resume_data.get('name', 'Name Not Provided')
        cleaned_data['email'] = resume_data.get('email', '')

        for field in ['phone', 'location', 'linkedin', 'github', 'portfolio']:
            val = resume_data.get(field, '')
            if isinstance(val, str):
                cleaned_data[field] = val.strip()

        summary = resume_data.get('summary', '')
        if isinstance(summary, str):
            cleaned_data['summary'] = summary.strip()

        skills = resume_data.get('skills', [])
        cleaned_data['skills'] = [s.strip() for s in skills if isinstance(s, str)]

        # Experience
        cleaned_experience = []
        for exp in resume_data.get('experience', []):
            if isinstance(exp, dict):
                desc = exp.get('description', [])
                if isinstance(desc, str):
                    desc = [desc]
                cleaned_exp = {
                    'company': exp.get('company', '').strip(),
                    'title': exp.get('title', '').strip(),
                    'duration': exp.get('duration', '').strip(),
                    'location': exp.get('location', '').strip(),
                    'description': [d.strip() for d in desc if isinstance(d, str) and d.strip()]
                }
                if cleaned_exp['company'] or cleaned_exp['title']:
                    cleaned_experience.append(cleaned_exp)
        cleaned_data['experience'] = cleaned_experience

        # Education
        cleaned_education = []
        for edu in resume_data.get('education', []):
            if isinstance(edu, dict):
                cleaned_edu = {
                    'institution': edu.get('institution', '').strip(),
                    'degree': edu.get('degree', '').strip(),
                    'duration': edu.get('duration', '').strip(),
                    'location': edu.get('location', '').strip(),
                    'gpa': edu.get('gpa', '').strip(),
                    'honors': edu.get('honors', '').strip(),
                }
                if cleaned_edu['institution'] or cleaned_edu['degree']:
                    cleaned_education.append(cleaned_edu)
        cleaned_data['education'] = cleaned_education

        # Projects
        cleaned_projects = []
        for proj in resume_data.get('projects', []):
            if isinstance(proj, dict):
                desc = proj.get('description', '')
                if isinstance(desc, str):
                    desc = desc.strip()
                elif isinstance(desc, list):
                    desc = [d.strip() for d in desc if isinstance(d, str)]
                cleaned_proj = {
                    'title': proj.get('title', '').strip(),
                    'description': desc,
                    'tech_stack': proj.get('tech_stack', '').strip(),
                    'link': proj.get('link', '').strip(),
                }
                if cleaned_proj['title']:
                    cleaned_projects.append(cleaned_proj)
        cleaned_data['projects'] = cleaned_projects

        cleaned_data['certifications'] = [
            c.strip() for c in resume_data.get('certifications', []) if isinstance(c, str)
        ]
        return cleaned_data

    def generate_latex_from_resume(self, resume_data: Dict) -> str:
        logging.info("Preprocessing resume data...")
        resume_data = self.preprocess_resume_data(self.validate_resume_data(resume_data))
        env = Environment(
            loader=FileSystemLoader(self.template_path),
            block_start_string='((*', block_end_string='*))',
            variable_start_string='(((', variable_end_string=')))',
            comment_start_string='((#', comment_end_string='#))',
            trim_blocks=True, lstrip_blocks=True, autoescape=False
        )
        env.filters['batch'] = self._batch_filter
        template = env.get_template("resume_template.tex.j2")
        return template.render(**resume_data)

    def _batch_filter(self, items, size):
        return [items[i:i + size] for i in range(0, len(items), size)] if items else []

    def check_latex_installation(self) -> Tuple[bool, str]:
        try:
            result = subprocess.run(['pdflatex', '--version'], capture_output=True, text=True, timeout=10)
            return (result.returncode == 0, result.stdout or result.stderr)
        except FileNotFoundError:
            return False, "pdflatex not found"
        except subprocess.TimeoutExpired:
            return False, "pdflatex check timed out"

    def render_resume_to_pdf(self, resume_data: Dict, output_dir: str, return_log=False):
        latex_ok, msg = self.check_latex_installation()
        if not latex_ok:
            return (None, msg) if return_log else None

        os.makedirs(output_dir, exist_ok=True)
        tex_file = os.path.join(output_dir, "resume.tex")
        pdf_file = os.path.join(output_dir, "resume.pdf")
        log_file = os.path.join(output_dir, "pdflatex.log")

        tex_content = self.generate_latex_from_resume(resume_data)
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(tex_content)

        def run_pdflatex():
            return subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-file-line-error", "resume.tex"],
                cwd=output_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60
            )

        result1 = run_pdflatex()
        result2 = run_pdflatex()
        combined_output = f"=== PASS1 ===\n{result1.stdout}\n{result1.stderr}\n\n=== PASS2 ===\n{result2.stdout}\n{result2.stderr}"

        with open(log_file, "w", encoding="utf-8") as f:
            f.write(combined_output)

        if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
            for ext in ['.aux', '.log', '.out', '.fdb_latexmk', '.fls', '.synctex.gz']:
                aux = os.path.join(output_dir, f"resume{ext}")
                if os.path.exists(aux):
                    try: os.remove(aux)
                    except: pass
            return (pdf_file, combined_output) if return_log else pdf_file
        else:
            return (None, combined_output) if return_log else None

# Factory function
def render_resume_to_pdf(resume_data: Dict, output_dir: str, return_log: bool = False):
    return EnhancedPDFGenerator().render_resume_to_pdf(resume_data, output_dir, return_log)
