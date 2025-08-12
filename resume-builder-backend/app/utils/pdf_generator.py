import os
import re
import subprocess
import logging
from jinja2 import Environment, FileSystemLoader
from typing import Dict, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EnhancedPDFGenerator:
    """Enhanced PDF generator with robust LaTeX escaping and data cleaning."""
    
    def __init__(self, template_path: str = None):
        self.template_path = (
            template_path
            or os.getenv("TEMPLATE_PATH", os.path.join(os.getcwd(), "app", "templates"))
        )
        
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
    
    # ---------------------------
    # LaTeX Escaping & URL Detection
    # ---------------------------
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

        # Regex escape
        pattern = re.compile('|'.join(re.escape(c) for c in self.latex_escape))
        return pattern.sub(lambda m: self.latex_escape[m.group()], text)

    def _is_url(self, text: str) -> bool:
        return isinstance(text, str) and text.lower().startswith(('http://', 'https://', 'www.', 'mailto:'))

    # ---------------------------
    # Resume Data Cleaning
    # ---------------------------
    def validate_resume_data(self, resume_data: Dict) -> Dict:
        """Validate, normalize, and deeply clean resume data to avoid empty LaTeX sections."""
        
        def _clean_str(val: str) -> Optional[str]:
            return val.strip() if isinstance(val, str) and val.strip() else None

        def _clean_list(lst):
            if not isinstance(lst, list):
                return []
            cleaned = [_clean_str(x) for x in lst if isinstance(x, str)]
            return [x for x in cleaned if x]  # remove None

        cleaned_data = {
            'name': _clean_str(resume_data.get('name')) or 'Name Not Provided',
            'email': _clean_str(resume_data.get('email')) or '',
            'phone': _clean_str(resume_data.get('phone')) or '',
            'location': _clean_str(resume_data.get('location')) or '',
            'linkedin': _clean_str(resume_data.get('linkedin')) or '',
            'github': _clean_str(resume_data.get('github')) or '',
            'portfolio': _clean_str(resume_data.get('portfolio')) or '',
            'summary': _clean_str(resume_data.get('summary')) or '',
            'skills': _clean_list(resume_data.get('skills', [])),
            'certifications': _clean_list(resume_data.get('certifications', [])),
        }

        # --- Experience ---
        cleaned_experience = []
        for exp in resume_data.get('experience', []):
            if isinstance(exp, dict):
                desc = exp.get('description', [])
                if isinstance(desc, str):
                    desc = [desc]
                if isinstance(desc, list):
                    desc = _clean_list(desc)
                
                cleaned_exp = {
                    'company': _clean_str(exp.get('company')) or '',
                    'title': _clean_str(exp.get('title')) or '',
                    'duration': _clean_str(exp.get('duration')) or '',
                    'location': _clean_str(exp.get('location')) or '',
                    'description': desc,
                }
                if cleaned_exp['company'] or cleaned_exp['title']:
                    cleaned_experience.append(cleaned_exp)
        cleaned_data['experience'] = cleaned_experience

        # --- Education ---
        cleaned_education = []
        for edu in resume_data.get('education', []):
            if isinstance(edu, dict):
                cleaned_edu = {
                    'institution': _clean_str(edu.get('institution')) or '',
                    'degree': _clean_str(edu.get('degree')) or '',
                    'duration': _clean_str(edu.get('duration')) or '',
                    'location': _clean_str(edu.get('location')) or '',
                    'gpa': _clean_str(edu.get('gpa')) or '',
                    'honors': _clean_str(edu.get('honors')) or '',
                }
                if cleaned_edu['institution'] or cleaned_edu['degree']:
                    cleaned_education.append(cleaned_edu)
        cleaned_data['education'] = cleaned_education

        # --- Projects ---
        cleaned_projects = []
        for proj in resume_data.get('projects', []):
            if isinstance(proj, dict):
                desc = proj.get('description', [])
                if isinstance(desc, str):
                    desc = [desc]
                if isinstance(desc, list):
                    desc = _clean_list(desc)
                
                cleaned_proj = {
                    'title': _clean_str(proj.get('title')) or '',
                    'description': desc,
                    'tech_stack': _clean_str(proj.get('tech_stack')) or '',
                    'link': _clean_str(proj.get('link')) or '',
                }
                if cleaned_proj['title'] or cleaned_proj['description']:
                    cleaned_projects.append(cleaned_proj)
        cleaned_data['projects'] = cleaned_projects

        # Optional: recursively remove empty lists/dicts
        return self._remove_empty(cleaned_data)

    def _remove_empty(self, obj):
        """Recursively remove empty lists, dicts, and strings."""
        if isinstance(obj, dict):
            return {k: self._remove_empty(v) for k, v in obj.items() if v not in [None, '', [], {}]}
        elif isinstance(obj, list):
            return [self._remove_empty(v) for v in obj if v not in [None, '', [], {}]]
        else:
            return obj

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

    # ---------------------------
    # LaTeX Rendering
    # ---------------------------
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

    # ---------------------------
    # PDF Rendering
    # ---------------------------
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
                    try:
                        os.remove(aux)
                    except:
                        pass
            return (pdf_file, combined_output) if return_log else pdf_file
        else:
            return (None, combined_output) if return_log else None

# Factory function
def render_resume_to_pdf(resume_data: Dict, output_dir: str, return_log: bool = False):
    return EnhancedPDFGenerator().render_resume_to_pdf(resume_data, output_dir, return_log)
