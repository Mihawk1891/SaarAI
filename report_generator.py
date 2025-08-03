import google.generativeai as genai
import os
import json
import re
import pandas as pd
from dotenv import load_dotenv
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

# Configure Gemini
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.startswith("AIza"):
        raise ValueError("Invalid or missing Gemini API key")
    
    genai.configure(api_key=api_key)
    logger.info("Gemini API configured successfully")
except Exception as e:
    logger.error(f"Gemini configuration failed: {e}")
    raise

# Gemini safety settings for educational context
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    }
]

class ReportGenerator:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def extract_subject_scores(self, row):
        subject_scores = {}
        for col in row.index:
            if '_C' in col and pd.notna(row[col]):
                subject = col.split('_')[0]
                scores = []
                for period in ['C', 'P1', 'P2']:
                    score_col = f"{subject}_{period}"
                    if score_col in row and pd.notna(row[score_col]):
                        scores.append(row[score_col])
                if len(scores) >= 2:  # Need at least 2 scores for comparison
                    subject_scores[subject] = scores
        return subject_scores
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    def analyze_scores(self, row):
        subject_scores = self.extract_subject_scores(row)
        if not subject_scores:
            return {"strengths": [], "improvements": [], "risks": []}
        
        # Format prompt for Gemini
        prompt = f"""
        ROLE: Educational Data Scientist
        TASK: Analyze academic performance data
        
        RAW SCORES:
        {json.dumps(subject_scores, indent=2)}
        
        INSTRUCTIONS:
        1. Calculate improvement percentage for each subject: 
           improvement = ((current - oldest)/oldest * 100)
        2. Identify top strength (subject with highest consistent scores)
        3. Flag subjects with >15% score drop as URGENT
        4. Format output as VALID JSON with these keys:
           - strengths: list of dictionaries with "subject" and "evidence"
           - improvements: list of dictionaries with "subject" and "trend" (percentage)
           - risks: list of dictionaries with "subject" and "drop" (percentage)
        
        OUTPUT ONLY JSON. No additional text or markdown.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                    max_output_tokens=1000,
                    response_mime_type="application/json"
                )
            )
            
            # Extract JSON from Gemini's response
            json_str = response.text.strip().replace('```json', '').replace('```', '')
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Score analysis failed: {e}")
            # Fallback if analysis fails
            return {
                "strengths": [{"subject": "General", "evidence": "Good overall performance"}],
                "improvements": [],
                "risks": []
            }
    
    def classify_vark(self, row):
        responses = []
        for i in range(1, 5):
            col = f'VARK_Q{i}'
            if col in row and pd.notna(row[col]):
                responses.append(row[col])
        
        if not responses:
            return 'Visual'  # Default
        
        vark_map = {'A': 'Visual', 'B': 'Aural', 'C': 'Read/Write', 'D': 'Kinesthetic'}
        primary_style = max(set(responses), key=responses.count)
        return vark_map.get(primary_style, 'Visual')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
    def generate_narrative(self, row, analysis, vark_profile, teacher_quote=""):
        # Prepare student data
        student_data = {
            "name": row.get('StudentName', 'Student'),
            "lang": row['LangPref'],
            "accessibility": row['AccPref']
        }
        
        # Format prompt for Gemini
        prompt = f"""
        **ROLE**: Educational Psychologist
        **LANGUAGE**: {student_data['lang']} (B1 Level)
        **STUDENT PROFILE**:
        - Name: {student_data['name']}
        - Learning Style: {vark_profile}
        - Accessibility Needs: {student_data['accessibility']}
        - Teacher Feedback: "{teacher_quote}"
        
        **PERFORMANCE ANALYSIS**:
        {json.dumps(analysis, indent=2)}
        
        **REQUIREMENTS**:
        1. Generate a 1-page student report in plain text format
        2. Structure with these sections:
        [Top Strength Highlight]
        [Learning Style Identification]
        [Strengths List]
        [Improvement Areas]
        [Teacher Quote]
        [Personalized Study Hacks]
        3. Start with ★ emoji for top strength
        4. Include teacher quote verbatim
        5. Suggest 2 {vark_profile}-specific study hacks
        6. Use growth mindset language
        7. Format for accessibility needs: {student_data['accessibility']}
        8. Write at B1 language level
        
        **OUTPUT INSTRUCTIONS**:
        - Use plain text with line breaks only
        - Never use markdown, HTML, or special formatting
        - Keep entire report under 1000 characters
        - Use emojis sparingly for emphasis
        - Include all sections from requirements
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1500
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            # Fallback content
            return f"""
            ★ Top Strength: General Academic Performance
            Learning Style: {vark_profile}
            
            STRENGTHS:
            - Good overall engagement
            
            IMPROVEMENT AREAS:
            - Focus on consistent practice
            
            TEACHER FEEDBACK:
            {teacher_quote}
            
            STUDY SUGGESTIONS:
            1. Try visual diagrams for complex concepts
            2. Review material regularly
            """