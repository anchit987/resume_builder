from openai import OpenAI
from app.config import LLM_API_KEY
import json
import re
from typing import Dict, Optional, List

# SambaNova-compatible OpenAI client
client = OpenAI(
    api_key=LLM_API_KEY,
    base_url="https://api.sambanova.ai/v1",
)

class EnhancedLLMHandler:
    """Enhanced LLM handler with better prompting and error handling."""
    
    @staticmethod
    def validate_json_response(response: str) -> tuple[bool, Optional[Dict], str]:
        """Validate and clean JSON response from LLM."""
        try:
            # Try to parse as-is first
            parsed = json.loads(response)
            return True, parsed, "Valid JSON"
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                return True, parsed, "JSON extracted from markdown"
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON-like content
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                return True, parsed, "JSON pattern extracted"
            except json.JSONDecodeError:
                pass
        
        return False, None, f"No valid JSON found in response: {response[:200]}..."
    
    @staticmethod
    def create_enhanced_prompt(resume_text: str, update_text: str = "") -> str:
        """Create an enhanced prompt for better resume parsing."""
        
        update_section = ""
        if update_text:
            update_section = f"""
IMPORTANT: The user has requested the following updates/changes:
{update_text}

Please incorporate these changes into the final output while maintaining accuracy.
"""

        prompt = f"""You are a professional resume parser and ATS optimization expert. Your task is to extract and structure resume information into a clean JSON format while enhancing readability and ATS compatibility.

INPUT RESUME:
---
{resume_text}
---

{update_section}

CRITICAL INSTRUCTIONS:

1. ACCURACY FIRST: Only extract information that is explicitly present in the resume. Never invent, assume, or hallucinate details.

2. FIELD HANDLING:
   - If a field is not present or unclear, omit it entirely from the JSON
   - Do not use placeholders like "N/A", "unknown", or empty strings
   - Maintain original factual content while improving language clarity

3. CONTENT ENHANCEMENT (without changing facts):
   - Rewrite job descriptions as strong, action-oriented bullet points
   - Use format: [Action Verb] + [What was accomplished] + [Quantified impact when possible]
   - Improve grammar and professional tone while keeping all facts intact
   - Make summary concise and impactful (2-3 sentences max)
   - Standardize company names, tech terms, and certifications

4. ATS OPTIMIZATION:
   - Use industry-standard job titles and skill names
   - Include relevant keywords naturally
   - Ensure consistent formatting and terminology
   - Remove special characters that might confuse ATS systems

5. STRUCTURED OUTPUT:
   - Return ONLY a valid JSON object
   - No markdown formatting, explanations, or additional text
   - Use the exact schema provided below
   - Ensure all strings are properly escaped

REQUIRED JSON SCHEMA:
{{
  "name": "Full legal name",
  "email": "primary@email.com",
  "phone": "formatted phone number",
  "location": "City, State" or "City, Country",
  "linkedin": "https://linkedin.com/in/username",
  "github": "https://github.com/username",
  "portfolio": "https://portfolio-url.com",
  "summary": "Professional summary optimized for ATS (2-3 sentences)",
  "skills": [
    "Technical skills categorized and formatted consistently"
  ],
  "experience": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "duration": "Start Date – End Date",
      "location": "City, State",
      "description": [
        "Achievement-focused bullet point with metrics when available",
        "Another accomplishment highlighting impact and results"
      ]
    }}
  ],
  "education": [
    {{
      "degree": "Degree Type and Field",
      "institution": "University/School Name",
      "duration": "Start Year – End Year",
      "location": "City, State",
      "gpa": "X.X/4.0",
      "honors": "Relevant honors or distinctions"
    }}
  ],
  "projects": [
    {{
      "title": "Project Name",
      "description": "Brief description highlighting technical skills and impact",
      "tech_stack": "Technologies used (comma-separated)",
      "link": "https://project-url.com"
    }}
  ],
  "certifications": [
    "Certification Name (Issuing Organization, Year)"
  ]
}}

QUALITY CHECKLIST:
- All contact information accurately extracted
- Job descriptions are action-oriented and quantified
- Skills are properly categorized and use standard terminology
- Dates are consistently formatted
- No fictional or assumed information added
- JSON is valid and complete
- Summary is compelling but truthful

OUTPUT: Return only the JSON object, nothing else."""

        return prompt
    
    def call_llm_with_resume(self, resume_text: str, update_text: str = "") -> str:
        """Enhanced LLM call with better error handling and retries."""
        try:
            prompt = self.create_enhanced_prompt(resume_text, update_text)
            
            response = client.chat.completions.create(
                model="Meta-Llama-3.3-70B-Instruct",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a professional resume parser. Return only valid JSON without any markdown formatting or explanations."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                top_p=0.1,
                max_tokens=4000
            )
            
            raw_response = response.choices[0].message.content
            
            # Validate and clean the response
            is_valid, parsed_json, validation_msg = self.validate_json_response(raw_response)
            
            if is_valid:
                # Return the cleaned JSON as string
                return json.dumps(parsed_json, indent=2)
            else:
                # If validation fails, try a simpler prompt
                return self._retry_with_simple_prompt(resume_text, update_text, validation_msg)
                
        except Exception as e:
            raise Exception(f"LLM processing failed: {str(e)}")
    
    def _retry_with_simple_prompt(self, resume_text: str, update_text: str, error_msg: str) -> str:
        """Retry with a simpler, more focused prompt."""
        simple_prompt = f"""Extract resume information and return as JSON only:

Resume text:
{resume_text[:2000]}  

Return valid JSON with fields: name, email, phone, location, linkedin, github, summary, skills (array), experience (array with company, title, duration, description array), education (array), projects (array), certifications (array).

JSON only, no markdown:"""

        try:
            response = client.chat.completions.create(
                model="Meta-Llama-3.3-70B-Instruct",
                messages=[{"role": "user", "content": simple_prompt}],
                temperature=0.1,
                max_tokens=3000
            )
            
            raw_response = response.choices[0].message.content
            is_valid, parsed_json, _ = self.validate_json_response(raw_response)
            
            if is_valid:
                return json.dumps(parsed_json, indent=2)
            else:
                raise Exception(f"Both attempts failed. Original error: {error_msg}")
                
        except Exception as e:
            raise Exception(f"Retry attempt failed: {str(e)}")

# Factory function for backward compatibility
def call_llm_with_resume(resume_text: str, update_text: str = "") -> str:
    """Backward compatible LLM handler function."""
    handler = EnhancedLLMHandler()
    return handler.call_llm_with_resume(resume_text, update_text)