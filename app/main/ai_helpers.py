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
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    return response.choices[0].message.content

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
