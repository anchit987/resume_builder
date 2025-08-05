from openai import OpenAI
from app.config import LLM_API_KEY
import json
import re
from typing import Dict, Optional

# SambaNova-compatible OpenAI client
client = OpenAI(
    api_key=LLM_API_KEY,
    base_url="https://api.sambanova.ai/v1",
)

class EnhancedLLMHandler:
    """Enhanced LLM handler for resume parsing with strict JSON validation and cleanup."""
    
    @staticmethod
    def validate_json_response(response: str) -> tuple[bool, Optional[Dict], str]:
        """Validate and clean JSON response from LLM."""
        try:
            # Try direct parsing first
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
    def clean_resume_json(parsed_json: dict) -> dict:
        """Clean and standardize the LLM JSON output."""
        
        # Normalize education fields
        for edu in parsed_json.get("education", []):
            # Standardize GPA format
            if "gpa" in edu and edu["gpa"]:
                gpa_str = edu["gpa"].strip()
                
                # Convert percentage to X.X/100 format
                perc_match = re.search(r"(\d+\.?\d*)%", gpa_str)
                if perc_match:
                    edu["gpa"] = f"{perc_match.group(1)}/100"
                
                # Convert single number to /10 scale
                elif re.fullmatch(r"\d+\.?\d*", gpa_str):
                    edu["gpa"] = f"{gpa_str}/10"
            
            # Remove honors if it's empty or just GPA-related
            if "honors" in edu:
                honors = edu["honors"].strip()
                if not honors or "cgpa" in honors.lower() or "gpa" in honors.lower():
                    edu.pop("honors", None)
        
        # Remove empty optional fields at the top level
        for key in ["linkedin", "github", "portfolio"]:
            if key in parsed_json and (not parsed_json[key] or parsed_json[key].strip() == ""):
                parsed_json.pop(key, None)
        
        return parsed_json

    @staticmethod
    def create_enhanced_prompt(resume_text: str, update_text: str = "", target_role: str = "software engineer") -> str:
        """Create an ATS-optimized prompt for resume parsing, adaptable to any target role."""
        
        # 1. Optional update instructions from user
        update_section = ""
        if update_text:
            update_section = f"""
IMPORTANT: The user requested these changes:
{update_text}
Please incorporate them while keeping accuracy intact.
"""

        # 2. Prompt now **lets the LLM infer keywords** instead of backend hardcoding
        prompt = f"""
You are a professional resume parser and ATS optimization expert.
Your task is to extract and enhance the resume into a clean, ATS-friendly JSON.

INPUT RESUME:
---
{resume_text}
---

{update_section}

CRITICAL INSTRUCTIONS:

1. ACCURACY FIRST:
   - Use only the data from the resume.
   - Do NOT invent companies, degrees, or dates.
   - You may rewrite bullet points to emphasize measurable impact and relevant technical skills.

2. ATS OPTIMIZATION:
   - Target role: {target_role}
   - **Identify and naturally integrate relevant industry keywords and skills** for this role.
   - Keywords should align with tools, technologies, and responsibilities common for {target_role}.
   - Rewrite summary & experience to highlight **action + impact + metrics**.
   - Skills must be grouped logically by category.

3. CONTENT ENHANCEMENT:
   - Expand each job experience into 3–5 **bullet points** with **action verbs** and **quantifiable metrics**.
   - Project descriptions should highlight **technical stack and outcomes**.
   - Summary: 2–3 sentences tailored to {target_role}, emphasizing achievements and core strengths.

4. EDUCATION & CERTIFICATIONS:
   - GPA must be in X.X/10 or NN.N% format.
   - Include only real honors/awards if mentioned with the degree.
   - Highlight certifications relevant to {target_role}.

5. OUTPUT REQUIREMENTS:
   - Return **ONLY valid JSON**, no markdown or extra explanation.
   - JSON schema:
{{
  "name": "Full legal name",
  "email": "primary@email.com",
  "phone": "formatted phone number",
  "location": "City, State or City, Country",
  "linkedin": "https://linkedin.com/in/username",
  "github": "https://github.com/username",
  "portfolio": "https://portfolio-url.com",
  "summary": "Professional summary tailored for {target_role}",
  "skills": [
    "Technical skills grouped logically"
  ],
  "experience": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "duration": "Start Date – End Date",
      "location": "City, State",
      "description": [
        "Action + metric bullet relevant to {target_role}",
        "Another bullet emphasizing impact or technical contribution"
      ]
    }}
  ],
  "education": [
    {{
      "degree": "Degree Type and Field",
      "institution": "University/School Name",
      "duration": "Start Year – End Year",
      "location": "City, State",
      "gpa": "X.X/10 or NN.N%",
      "honors": "Only real awards/distinctions"
    }}
  ],
  "projects": [
    {{
      "title": "Project Name",
      "description": "Brief description emphasizing relevant skills and outcomes",
      "tech_stack": "Technologies used (comma-separated)",
      "link": "https://project-url.com"
    }}
  ],
  "certifications": [
    "Certification Name (Issuing Organization, Year)"
  ]
}}

QUALITY CHECKLIST:
- JSON only (no markdown, no extra text)
- Experience shows **action + impact**
- Skills grouped logically
- Summary optimized for {target_role}
- Role-specific keywords included naturally
"""
        return prompt

    def call_llm_with_resume(self, resume_text: str, update_text: str = "", target_role: str = "") -> str:
        """Enhanced LLM call with error handling, retries, and post-processing."""
        try:
            prompt = self.create_enhanced_prompt(resume_text, update_text, target_role)

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
                cleaned_json = self.clean_resume_json(parsed_json)
                return json.dumps(cleaned_json, indent=2)
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

Return valid JSON with fields: name, email, phone, location, linkedin, github, summary, skills (array), experience (array with company, title, duration, description array), education (array with gpa and honors), projects (array), certifications (array).

Rules:
- GPA: X.X/10 or NN.N
- Honors: Only real awards/distinctions
- No empty strings, omit missing fields

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
                cleaned_json = self.clean_resume_json(parsed_json)
                return json.dumps(cleaned_json, indent=2)
            else:
                raise Exception(f"Both attempts failed. Original error: {error_msg}")
                
        except Exception as e:
            raise Exception(f"Retry attempt failed: {str(e)}")

# Factory function for backward compatibility
def call_llm_with_resume(self, resume_text: str, update_text: str = "", target_role: str = "") -> str:
    """Backward compatible LLM handler function."""
    handler = EnhancedLLMHandler()
    return handler.call_llm_with_resume(resume_text, update_text, target_role)
