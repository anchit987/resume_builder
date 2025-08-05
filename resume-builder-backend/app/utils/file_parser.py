import pdfplumber
import docx
import re
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Basic text cleanup with whitespace normalization."""
    if not text:
        return ""
    try:
        # Split into lines and normalize spaces
        lines = [' '.join(line.split()) for line in text.split('\n')]
        cleaned_lines = [line for line in lines if line.strip()]
        # Reduce multiple newlines
        result = '\n'.join(cleaned_lines)
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        return result.strip()
    except Exception as e:
        logger.warning(f"Text cleaning failed: {e}")
        return text.strip()

def clean_for_latex(text: str) -> str:
    """Escapes LaTeX special characters but keeps % as \%."""
    if not isinstance(text, str):
        return text
    special_chars = {
        "&": r"\&",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}"
    }
    for char, escaped in special_chars.items():
        text = text.replace(char, escaped)
    # Escape % last
    text = text.replace("%", r"\%")
    return text

def extract_contact_info(text: str) -> Dict[str, List[str]]:
    """Extract email, phone, LinkedIn, GitHub links."""
    contact_info = {}
    try:
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if emails:
            contact_info['emails'] = sorted(set(emails))

        phones = []
        phone_patterns = [
            r'\b\d{10}\b',  # 10 digits
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}'
        ]
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        if phones:
            cleaned_phones = []
            for phone in phones:
                digits = re.sub(r'\D', '', phone)
                if len(digits) == 10:
                    cleaned_phones.append(phone.strip())
            contact_info['phones'] = sorted(set(cleaned_phones))

        linkedin_matches = re.findall(r'linkedin\.com/in/[^\s]+', text, re.IGNORECASE)
        if linkedin_matches:
            contact_info['linkedin'] = sorted(set(linkedin_matches))

        github_matches = re.findall(r'github\.com/[^\s]+', text, re.IGNORECASE)
        if github_matches:
            contact_info['github'] = sorted(set(github_matches))

    except Exception as e:
        logger.warning(f"Contact extraction failed: {e}")
        contact_info['extraction_error'] = str(e)

    return contact_info

def parse_pdf(file_path: str, latex_ready: bool=False) -> str:
    """Parse PDF and optionally return LaTeX-safe text."""
    try:
        logger.info(f"Parsing PDF: {file_path}")
        full_text = ""
        with pdfplumber.open(file_path) as pdf:
            logger.info(f"PDF pages: {len(pdf.pages)}")
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text() or ""
                if len(page_text.strip()) < 20:
                    try:
                        page_text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                    except Exception as e:
                        logger.warning(f"Alt extraction failed on page {page_num}: {e}")
                        page_text = ""
                if page_text.strip():
                    full_text += f"\n=== PAGE {page_num} ===\n{page_text}\n"
                # Extract tables if text is sparse
                if len(page_text.strip()) < 50:
                    try:
                        for table in page.find_tables():
                            table_data = table.extract()
                            if table_data:
                                table_text = "\n".join([" | ".join([str(c or '') for c in row]) for row in table_data])
                                full_text += f"\n[TABLE DATA]\n{table_text}\n"
                    except Exception as e:
                        logger.warning(f"Table extraction failed page {page_num}: {e}")
        cleaned_text = clean_text(full_text)
        if latex_ready:
            cleaned_text = clean_for_latex(cleaned_text)
        return cleaned_text
    except Exception as e:
        logger.error(f"PDF parsing failed: {str(e)}")
        raise

def parse_docx(file_path: str, latex_ready: bool=False) -> str:
    """Parse DOCX and optionally return LaTeX-safe text."""
    try:
        logger.info(f"Parsing DOCX: {file_path}")
        doc = docx.Document(file_path)
        full_text = ""
        for para in doc.paragraphs:
            if para.text.strip():
                full_text += para.text + "\n"
        for table in doc.tables:
            full_text += "\n[TABLE]\n"
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    full_text += row_text + "\n"
            full_text += "[/TABLE]\n\n"
        cleaned_text = clean_text(full_text)
        if latex_ready:
            cleaned_text = clean_for_latex(cleaned_text)
        return cleaned_text
    except Exception as e:
        logger.error(f"DOCX parsing failed: {str(e)}")
        raise

def test_parser(file_path: str, latex_ready: bool=False):
    """Test parsing and show sample output with contact info."""
    ext = file_path.lower().split('.')[-1]
    text = parse_pdf(file_path, latex_ready) if ext == 'pdf' else \
           parse_docx(file_path, latex_ready) if ext == 'docx' else None
    if not text:
        return "Unsupported file type"
    print(f"Extracted {len(text)} chars\nFirst 500 chars:\n{text[:500]}")
    print("\nContact info:", extract_contact_info(text))
    return text
