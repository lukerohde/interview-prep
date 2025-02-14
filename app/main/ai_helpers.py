import os
import json
from openai import OpenAI
from typing import List, Dict

def call_openai(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a system prompt and user prompt to OpenAI and returns the response.
    
    Parameters:
        system_prompt (str): The system-level instructions for the AI.
        user_prompt (str): The user's input or query.
    
    Returns:
        str: The response from OpenAI.
    """
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content

def generate_interview_questions(job_description: str, resume: str, existing_questions: List[Dict] = None) -> List[Dict]:
    """
    Generate interview questions based on the job description and resume.
    
    Parameters:
        job_description (str): The job description text
        resume (str): The resume text
        existing_questions (List[Dict]): List of existing questions to avoid duplicates
        
    Returns:
        List[Dict]: List of generated questions with their categories and suggested answers
    """
    system_prompt = """
    You are an expert interviewer tasked with generating relevant interview questions. 
    Create a diverse set of interview questions that cover:
    1. Standard HR questions
    2. Cultural fit questions
    3. Ways of working questions
    4. Resume-specific questions (including gaps and mismatches)
    5. Technical questions to validate skills
    
    For each question, provide:
    - The question text
    - The category it belongs to
    - A suggested approach or key points for answering (in STAR format where applicable)
    
    Ensure questions are specific to the job and candidate's background.
    Format the response as a JSON array of objects with 'question', 'category', and 'suggested_answer' keys.
    """
    
    existing_questions_text = "\n\nExisting questions to avoid:\n" + \
        json.dumps([q['question'] for q in (existing_questions or [])]) if existing_questions else ""
    
    user_prompt = f"""
    Job Description:
    {job_description}
    
    Resume:
    {resume}
    {existing_questions_text}
    
    As a professional interviewer, generate a set of unique interview questions based on this information.
    """
    
    response = call_openai(system_prompt, user_prompt)
    try:
        questions = json.loads(response)
        return questions
    except json.JSONDecodeError:
        # If the response isn't valid JSON, try to extract questions manually or return empty list
        return []