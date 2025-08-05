import os
import subprocess
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Dict, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class EnhancedPDFGenerator:
    """Enhanced PDF generator with better error handling and template management."""
    
    def __init__(self, template_path: str = None):
        self.template_path = template_path or r"C://Users//HP//Desktop//resumebuilder//resume_builder//resume-builder-backend//app//templates"
        
        # Enhanced LaTeX escape dictionary
        self.latex_escape = {
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
            "|": r"\textbar{}",
            "<": r"\textless{}",
            ">": r"\textgreater{}",
            '"': r"\textquotedbl{}",
        }
        
        # Fields that should not be escaped (URLs, etc.)
        self.no_escape_keys = {"website", "linkedin", "github", "portfolio", "link"}
    
    def escape_latex(self, text):
        """Enhanced LaTeX escaping with better handling of edge cases."""
        if not text or not isinstance(text, str):
            return text
        
        # Handle common problematic patterns first
        text = text.replace("–", "--")  # En dash
        text = text.replace("—", "---")  # Em dash
        text = text.replace("’", "'")   # Right single quote
        text = text.replace("‘", "'")   # Left single quote
        text = text.replace("“", '"')   # Left double quote
        text = text.replace("”", '"')   # Right double quote
        
        # Apply standard escaping
        for char, replacement in self.latex_escape.items():
            text = text.replace(char, replacement)
        
        return text
    
    def preprocess_resume_data(self, data, parent_key=None):
        """Recursively escape LaTeX characters with improved handling."""
        if isinstance(data, dict):
            return {k: self.preprocess_resume_data(v, k) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.preprocess_resume_data(v, parent_key) for v in data]
        elif isinstance(data, str):
            # Don't escape URLs and certain fields
            if parent_key in self.no_escape_keys or self._is_url(data):
                return data
            return self.escape_latex(data)
        return data
    
    def _is_url(self, text: str) -> bool:
        """Check if text is a URL."""
        if not isinstance(text, str):
            return False
        return text.startswith(('http://', 'https://', 'www.', 'mailto:'))
    
    def validate_resume_data(self, resume_data: Dict) -> Dict:
        """Validate and clean resume data before processing."""
        cleaned_data = {}
        
        # Required fields with defaults
        cleaned_data['name'] = resume_data.get('name', 'Name Not Provided')
        cleaned_data['email'] = resume_data.get('email', '')
        
        # Optional contact fields
        for field in ['phone', 'location', 'linkedin', 'github', 'portfolio']:
            value = resume_data.get(field, '')
            if value and isinstance(value, str):
                cleaned_data[field] = value.strip()
        
        # Summary
        summary = resume_data.get('summary', '')
        if summary and isinstance(summary, str):
            cleaned_data['summary'] = summary.strip()
        
        # Skills
        skills = resume_data.get('skills', [])
        if isinstance(skills, list):
            cleaned_data['skills'] = [skill.strip() for skill in skills if skill and isinstance(skill, str)]
        
        # Experience
        experience = resume_data.get('experience', [])
        if isinstance(experience, list):
            cleaned_experience = []
            for exp in experience:
                if isinstance(exp, dict):
                    cleaned_exp = {
                        'company': exp.get('company', '').strip(),
                        'title': exp.get('title', '').strip(),
                        'duration': exp.get('duration', '').strip(),
                        'location': exp.get('location', '').strip(),
                        'description': []
                    }
                    
                    # Handle description field
                    desc = exp.get('description', [])
                    if isinstance(desc, list):
                        cleaned_exp['description'] = [d.strip() for d in desc if d and isinstance(d, str)]
                    elif isinstance(desc, str) and desc.strip():
                        cleaned_exp['description'] = [desc.strip()]
                    
                    if cleaned_exp['company'] or cleaned_exp['title']:
                        cleaned_experience.append(cleaned_exp)
            
            cleaned_data['experience'] = cleaned_experience
        
        # Education
        education = resume_data.get('education', [])
        if isinstance(education, list):
            cleaned_education = []
            for edu in education:
                if isinstance(edu, dict):
                    cleaned_edu = {
                        'institution': edu.get('institution', '').strip(),
                        'degree': edu.get('degree', '').strip(),
                        'duration': edu.get('duration', '').strip(),
                        'location': edu.get('location', '').strip(),
                        'gpa': edu.get('gpa', '').strip(),
                        'honors': edu.get('honors', '').strip()
                    }
                    
                    if cleaned_edu['institution'] or cleaned_edu['degree']:
                        cleaned_education.append(cleaned_edu)
            
            cleaned_data['education'] = cleaned_education
        
        # Projects
        projects = resume_data.get('projects', [])
        if isinstance(projects, list):
            cleaned_projects = []
            for proj in projects:
                if isinstance(proj, dict):
                    cleaned_proj = {
                        'title': proj.get('title', '').strip(),
                        'description': proj.get('description', ''),
                        'tech_stack': proj.get('tech_stack', '').strip(),
                        'link': proj.get('link', '').strip()
                    }
                    
                    # Handle description (can be string or list)
                    if isinstance(cleaned_proj['description'], list):
                        cleaned_proj['description'] = [d.strip() for d in cleaned_proj['description'] if d and isinstance(d, str)]
                    elif isinstance(cleaned_proj['description'], str):
                        cleaned_proj['description'] = cleaned_proj['description'].strip()
                    
                    if cleaned_proj['title']:
                        cleaned_projects.append(cleaned_proj)
            
            cleaned_data['projects'] = cleaned_projects
        
        # Certifications
        certifications = resume_data.get('certifications', [])
        if isinstance(certifications, list):
            cleaned_data['certifications'] = [cert.strip() for cert in certifications if cert and isinstance(cert, str)]
        
        return cleaned_data
    
    def generate_latex_from_resume(self, resume_data: Dict) -> str:
        """Generate LaTeX content from resume data."""
        logging.info("Validating and preprocessing resume data...")
        resume_data = self.validate_resume_data(resume_data)
        resume_data = self.preprocess_resume_data(resume_data)
        
        logging.info(f"Loading Jinja2 environment from: {self.template_path}")
        env = Environment(
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
        
        # Add custom filters
        env.filters['batch'] = self._batch_filter
        
        template_name = "resume_template.tex.j2"
        logging.info(f"Loading LaTeX template: {template_name}")
        
        try:
            template = env.get_template(template_name)
        except Exception as e:
            logging.error(f"Template loading failed: {e}")
            raise Exception(f"Failed to load template {template_name}: {str(e)}")
        
        logging.info("Rendering LaTeX content...")
        try:
            return template.render(**resume_data)
        except Exception as e:
            logging.error(f"Template rendering failed: {e}")
            raise Exception(f"Failed to render template: {str(e)}")
    
    def _batch_filter(self, items, size):
        """Custom Jinja2 filter to batch items into groups."""
        if not items:
            return []
        return [items[i:i + size] for i in range(0, len(items), size)]
    
    def check_latex_installation(self) -> Tuple[bool, str]:
        """Check if LaTeX is properly installed."""
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, "LaTeX installation found"
            else:
                return False, f"LaTeX check failed: {result.stderr}"
        except FileNotFoundError:
            return False, "pdflatex not found. Please install LaTeX (e.g., MiKTeX or TeX Live)"
        except subprocess.TimeoutExpired:
            return False, "LaTeX check timed out"
        except Exception as e:
            return False, f"LaTeX check error: {str(e)}"
    
    def render_resume_to_pdf(self, resume_data: Dict, output_dir: str, return_log: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """Enhanced PDF rendering with better error handling."""
        logging.info("Starting PDF generation...")
        
        # Check LaTeX installation
        latex_ok, latex_msg = self.check_latex_installation()
        if not latex_ok:
            error_msg = f"LaTeX not available: {latex_msg}"
            logging.error(error_msg)
            if return_log:
                return None, error_msg
            return None
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Generate LaTeX content
            tex_content = self.generate_latex_from_resume(resume_data)
            
            # File paths
            tex_file = os.path.join(output_dir, "resume.tex")
            pdf_file = os.path.join(output_dir, "resume.pdf")
            log_file = os.path.join(output_dir, "pdflatex.log")
            
            # Write LaTeX file
            logging.info(f"Writing LaTeX to: {tex_file}")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(tex_content)
            
            # Run pdflatex twice
            def run_pdflatex():
                return subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-file-line-error", "resume.tex"],
                    cwd=output_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60
                )
            
            logging.info(f"Running pdflatex in: {output_dir}")
            result1 = run_pdflatex()
            result2 = run_pdflatex()
            
            # Combine output from both passes
            combined_output = f"=== FIRST PASS ===\n{result1.stdout}\n{result1.stderr}\n\n=== SECOND PASS ===\n{result2.stdout}\n{result2.stderr}"
            
            # Save logs
            logging.info("Saving pdflatex logs...")
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(combined_output)
            
            # Check if PDF was created successfully
            if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
                logging.info(f"PDF generation succeeded: {pdf_file}")
                
                # Clean up auxiliary files
                aux_extensions = ['.aux', '.log', '.out', '.fdb_latexmk', '.fls', '.synctex.gz']
                for ext in aux_extensions:
                    aux_file = os.path.join(output_dir, f"resume{ext}")
                    if os.path.exists(aux_file):
                        try:
                            os.remove(aux_file)
                        except:
                            pass  # Ignore cleanup errors
                
                return (pdf_file, combined_output) if return_log else pdf_file
            else:
                error_msg = f"PDF generation failed. LaTeX errors:\n{combined_output}"
                logging.error(error_msg)
                return (None, error_msg) if return_log else None
                
        except subprocess.TimeoutExpired:
            error_msg = "PDF generation timed out (60 seconds)"
            logging.error(error_msg)
            return (None, error_msg) if return_log else None
            
        except Exception as e:
            error_msg = f"PDF generation failed with exception: {str(e)}"
            logging.error(error_msg)
            return (None, error_msg) if return_log else None

# Factory function for backward compatibility
def render_resume_to_pdf(resume_data: Dict, output_dir: str, return_log: bool = False):
    """Backward compatible PDF rendering function."""
    generator = EnhancedPDFGenerator()
    return generator.render_resume_to_pdf(resume_data, output_dir, return_log)
