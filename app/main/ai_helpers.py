import os
from openai import OpenAI

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