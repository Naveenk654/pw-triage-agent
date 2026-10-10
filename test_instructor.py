import os
import instructor
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class TestModel(BaseModel):
    name: str
    age: int

try:
    client = instructor.from_openai(OpenAI(
        api_key=os.environ.get("MISTRAL_API_KEY"),
        base_url="https://api.mistral.ai/v1"
    ))
    res = client.chat.completions.create(
        model="mistral-small-latest",
        response_model=TestModel,
        messages=[{"role": "user", "content": "My name is John and I am 25 years old."}]
    )
    print(f"SUCCESS: {res}")
except Exception as e:
    print(f"ERROR: {e}")
