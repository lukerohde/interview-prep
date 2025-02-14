import pytest
from main.ai_helpers import extract_json

def test_extract_json_direct():
    """Test extracting direct JSON string"""
    json_str = '[{"question": "Test?", "answer": "Yes"}]'
    result = extract_json(json_str)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["question"] == "Test?"
    assert result[0]["answer"] == "Yes"

def test_extract_json_from_markdown_block():
    """Test extracting JSON from markdown code block"""
    markdown_str = '''
    Here is the response:
    ```json
    [{"question": "Test?", "answer": "Yes"}]
    ```
    '''
    result = extract_json(markdown_str)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["question"] == "Test?"
    assert result[0]["answer"] == "Yes"

def test_extract_json_from_plain_code_block():
    """Test extracting JSON from plain markdown code block"""
    markdown_str = '''
    Here is the response:
    ```
    [{"question": "Test?", "answer": "Yes"}]
    ```
    '''
    result = extract_json(markdown_str)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["question"] == "Test?"
    assert result[0]["answer"] == "Yes"

def test_extract_json_from_embedded_array():
    """Test extracting JSON array from text"""
    text = '''
    Here is what I found:
    The questions are: [{"question": "Test?", "answer": "Yes"}]
    Hope this helps!
    '''
    result = extract_json(text)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["question"] == "Test?"
    assert result[0]["answer"] == "Yes"

def test_extract_json_invalid():
    """Test handling invalid JSON"""
    invalid_inputs = [
        "Not JSON at all",
        "```json\nNot JSON either\n```",
        "[Not valid JSON]",
        '{"incomplete": "json"',
    ]
    for invalid_input in invalid_inputs:
        result = extract_json(invalid_input)
        assert isinstance(result, list)
        assert len(result) == 0

def test_extract_json_complex():
    """Test extracting complex JSON with nested structures"""
    json_str = '''
    ```json
    [
        {
            "question": "What is your experience with Python?",
            "category": "Technical",
            "suggested_answer": {
                "key_points": ["Experience level", "Projects"],
                "format": "STAR",
                "examples": ["Project A", "Project B"]
            }
        }
    ]
    ```
    '''
    result = extract_json(json_str)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["question"] == "What is your experience with Python?"
    assert result[0]["category"] == "Technical"
    assert isinstance(result[0]["suggested_answer"], dict)
    assert "key_points" in result[0]["suggested_answer"]
    assert "format" in result[0]["suggested_answer"]
    assert "examples" in result[0]["suggested_answer"]
