from openai import OpenAI
from app.config import LLM_API_KEY

# SambaNova-compatible OpenAI client
client = OpenAI(
    api_key=LLM_API_KEY,
    base_url="https://api.sambanova.ai/v1",
)

def call_llm_with_resume(resume_text: str, update_text: str = "") -> str:
    update_block = f"\nThe user has requested the following updates:\n{update_text}" if update_text else ""

    prompt = f"""
You are an expert AI resume structuring assistant.

You will be given resume text and optional update instructions (e.g., "change job title", "update summary", etc.). You must return a structured JSON document that strictly represents the resume content without hallucination, inference, or fabrication.

<<<BEGIN_RESUME>>>
{resume_text}
<<<END_RESUME>>>

{update_block}

Strict Formatting & Output Instructions:

1. Only extract information explicitly present in the resume or user-provided updates. Do NOT infer, assume, or hallucinate any details.

2. DO NOT use placeholders like "N/A", "unknown", or "not provided". If a field is not present, leave it out entirely from the JSON.

3. Maintain a clean and consistent structure. Return a single valid JSON object only — without extra formatting, markdown, or commentary.

4. Enhance only language clarity and formatting (not content):
   - Reword job descriptions into professional, action-driven bullet points using the format:  
     [Strong Action Verb] [What was done] [Impact or Result] — include metrics if available.
   - Rephrase the summary to be concise, impactful, and ATS-friendly (max 3 lines).
   - Capitalize tech stack and company names consistently.

5. For any list-type fields (like skills, certifications, projects), ensure:
   - Each item is clear and succinct.
   - Avoid repetitions or vague words like "etc.", "many", "various".

6. Do not include empty lists or empty string fields in the final output.

7. Keep content authentic to the resume, but refine the writing for grammar, clarity, and recruiter appeal (only where it's explicitly stated).

8. Prefer metric-backed statements where available. e.g., "Reduced processing time by 30%" is better than "Improved processing".

Return a single, clean, and complete JSON object with these keys (omit if not present):

{{
  "name": "Full Name",
  "email": "email@domain.com",
  "phone": "+1-123-456-7890",
  "location": "City, State",
  "linkedin": "https://linkedin.com/in/username",
  "github": "https://github.com/username",
  "portfolio": "https://portfolio.com",
  "summary": "2–3 sentence professional summary",
  "skills": ["Skill 1", "Skill 2", "..."],
  "experience": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "duration": "Month Year – Month Year",
      "location": "City, State",
      "description": [
        "[Action Verb] [What you did] [Quantified outcome]",
        ...
      ]
    }}
  ],
  "education": [
    {{
      "degree": "Degree",
      "institution": "School Name",
      "duration": "Month Year – Month Year",
      "location": "City, State",
      "gpa": "3.5/4.0"
    }}
  ],
  "projects": [
    {{
      "title": "Project Name",
      "description": "1–2 line summary",
      "tech_stack": "Python, React, MongoDB",
      "link": "https://github.com/project"
    }}
  ],
  "certifications": ["Certificate A", "Certificate B"]
}}
"""

    response = client.chat.completions.create(
        model="Meta-Llama-3.3-70B-Instruct",
        messages=[
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ],
        temperature=0.1,
        top_p=0.1
    )

    return response.choices[0].message.content
