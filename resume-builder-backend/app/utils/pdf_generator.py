import os
import re
import subprocess
import logging
from jinja2 import Environment, FileSystemLoader, Template
from typing import Dict, Tuple, Optional
from datetime import datetime
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EnhancedPDFGenerator:
    """Enhanced PDF generator with robust LaTeX escaping and data cleaning."""
    
    # Pre-compile regex patterns
    URL_PATTERN = re.compile(r'^(http://|https://|www\.|mailto:)', re.IGNORECASE)
    LATEX_ESCAPE_PATTERN = None  # Will be set in __init__
    
    def __init__(self, template_path: str = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_template_path = os.path.join(base_dir, "templates")

        self.template_path = (
            template_path
            or os.getenv("TEMPLATE_PATH", default_template_path)
        )

        if not os.path.isdir(self.template_path):
            raise FileNotFoundError(
                f"Template directory not found: {self.template_path}"
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
        
        # Pre-compile the regex pattern
        self.__class__.LATEX_ESCAPE_PATTERN = re.compile('|'.join(re.escape(c) for c in self.latex_escape))
        
        self.no_escape_keys = frozenset({"website", "linkedin", "github", "portfolio", "link"})
        
        # Initialize Jinja environment once
        self.env = Environment(
            loader=FileSystemLoader(self.template_path),
            block_start_string='((*', 
            block_end_string='*))',
            variable_start_string='(((', 
            variable_end_string=')))',
            comment_start_string='((#', 
            comment_end_string='#))',
            trim_blocks=True, 
            lstrip_blocks=True, 
            autoescape=False
        )
        self.env.filters['batch'] = self._batch_filter
        
        # Cache the template
        self._template = self.env.get_template("resume_template.tex.j2")

    @lru_cache(maxsize=1024)
    def escape_latex(self, text: str) -> str:
        """Escape LaTeX special characters with caching."""
        if not text or not isinstance(text, str):
            return text

        # First replace special characters using string replacement
        replacements = {
            "–": "-",     # En dash
            "—": "---",   # Em dash
            "'": "'",     # Smart single quote (left)
            "'": "'",     # Smart single quote (right)
            """: "\"",    # Smart double quote (left)
            """: "\""     # Smart double quote (right)
        }
        
        # Replace special characters one by one
        for old, new in replacements.items():
            text = text.replace(old, new)

        # Then escape LaTeX special characters
        return self.LATEX_ESCAPE_PATTERN.sub(lambda m: self.latex_escape[m.group()], text)

    def _is_url(self, text: str) -> bool:
        return isinstance(text, str) and bool(self.URL_PATTERN.match(text))

    @staticmethod
    def _clean_str(val: str) -> Optional[str]:
        return val.strip() if isinstance(val, str) and val.strip() else None

    @staticmethod
    def _clean_list(lst):
        if not isinstance(lst, list):
            return []
        return [x.strip() for x in lst if isinstance(x, str) and x.strip()]

    # ---------------------------
    # Resume Data Cleaning
    # ---------------------------
    def validate_resume_data(self, resume_data: Dict) -> Dict:
        """Validate, normalize, and deeply clean resume data to avoid empty LaTeX sections."""
        

        cleaned_data = {
            'name': self._clean_str(resume_data.get('name')) or 'Name Not Provided',
            'email': self._clean_str(resume_data.get('email')) or '',
            'phone': self._clean_str(resume_data.get('phone')) or '',
            'location': self._clean_str(resume_data.get('location')) or '',
            'linkedin': self._clean_str(resume_data.get('linkedin')) or '',
            'github': self._clean_str(resume_data.get('github')) or '',
            'portfolio': self._clean_str(resume_data.get('portfolio')) or '',
            'summary': self._clean_str(resume_data.get('summary')) or '',
            'skills': self._clean_list(resume_data.get('skills', [])),
            'certifications': self._clean_list(resume_data.get('certifications', [])),
        }

        # --- Experience ---
        cleaned_experience = []
        for exp in resume_data.get('experience', []):
            if isinstance(exp, dict):
                desc = exp.get('description', [])
                if isinstance(desc, str):
                    desc = [desc]
                if isinstance(desc, list):
                    desc = self._clean_list(desc)
                
                cleaned_exp = {
                    'company': self._clean_str(exp.get('company')) or '',
                    'title': self._clean_str(exp.get('title')) or '',
                    'duration': self._clean_str(exp.get('duration')) or '',
                    'location': self._clean_str(exp.get('location')) or '',
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
                    'institution': self._clean_str(edu.get('institution')) or '',
                    'degree': self._clean_str(edu.get('degree')) or '',
                    'duration': self._clean_str(edu.get('duration')) or '',
                    'location': self._clean_str(edu.get('location')) or '',
                    'gpa': self._clean_str(edu.get('gpa')) or '',
                    'honors': self._clean_str(edu.get('honors')) or '',
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
                    desc = self._clean_list(desc)
                
                cleaned_proj = {
                    'title': self._clean_str(proj.get('title')) or '',
                    'description': desc,
                    'tech_stack': self._clean_str(proj.get('tech_stack')) or '',
                    'link': self._clean_str(proj.get('link')) or '',
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
        return self._template.render(**resume_data)

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
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Use more efficient file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"resume_{timestamp}"
            tex_file = os.path.join(output_dir, f"{base_name}.tex")
            pdf_file = os.path.join(output_dir, f"{base_name}.pdf")

            # Generate LaTeX content
            tex_content = self.generate_latex_from_resume(resume_data)
            
            # Use context manager for file operations
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(tex_content)

            # Run pdflatex with optimized parameters
            process = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-file-line-error", 
                 "-halt-on-error", "-output-directory", output_dir, tex_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            log_content = f"=== PDFLATEX OUTPUT ===\n{process.stdout}\n{process.stderr}"

            if not os.path.exists(pdf_file) or os.path.getsize(pdf_file) == 0:
                return (None, log_content) if return_log else None

            # Clean up in a single loop
            for ext in ['.aux', '.log', '.out', '.tex']:
                try:
                    aux_file = os.path.join(output_dir, f"{base_name}{ext}")
                    if os.path.exists(aux_file):
                        os.unlink(aux_file)
                except OSError:
                    pass

            return (pdf_file, log_content) if return_log else pdf_file

        except Exception as e:
            error_msg = f"PDF generation failed: {str(e)}"
            logging.error(error_msg)
            return (None, error_msg) if return_log else None

# Factory function
def render_resume_to_pdf(resume_data: Dict, output_dir: str, return_log: bool = False):
    return EnhancedPDFGenerator().render_resume_to_pdf(resume_data, output_dir, return_log)
