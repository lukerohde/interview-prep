import os
import json
from openai import OpenAI
from typing import List, Dict
from django.conf import settings
import re
       

def call_openai(system_prompt: str, user_prompt: str) -> str:
    """
    Sends a system prompt and user prompt to OpenAI and returns the response.
    
    Parameters:
        system_prompt (str): The system-level instructions for the AI.
        user_prompt (str): The user's input or query.
    
    Returns:
        str: The response from OpenAI.
    
    Raises:
        Exception: If called during tests without being mocked.
    """
    
    # In test environment, this function must be mocked.  Playing it safe. 
    if getattr(settings, 'TESTING', False):
        raise Exception("THIS SHOULD BE MOCKED IN TESTS")
    
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
    - A suggested approach or key points for answering (in STAR format where applicable), given the user's resume and job description
    
    A good format for your suggested answer looks like this.  
    `Provide an experience (Situation) related to team culture that needed improvement (Task), present your activities (Action), and show how these led to improved team dynamics (Result).`
    
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
    data = extract_json(response)
    return data

def extract_json(text: str) -> List[Dict]:
    """
    Extract JSON from a string that might contain markdown code blocks.
    The JSON could be directly in the string or within ```json blocks.
    
    Parameters:
        text (str): The text containing JSON data
        
    Returns:
        List[Dict]: Parsed JSON data or empty list if no valid JSON found
    """
    # First try to parse the entire response as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Look for JSON in code blocks
    # Match content between ```json and ``` or between ``` and ``` if it looks like JSON
    json_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.finditer(json_block_pattern, text)
    
    for match in matches:
        try:
            json_str = match.group(1).strip()
            return json.loads(json_str)
        except json.JSONDecodeError:
            continue
    
    # If we still haven't found valid JSON, try to find anything between square brackets
    # that might be a JSON array
    array_pattern = r'\[\s*{[\s\S]*?}\s*\]'
    matches = re.finditer(array_pattern, text)
    
    for match in matches:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
    
    return []