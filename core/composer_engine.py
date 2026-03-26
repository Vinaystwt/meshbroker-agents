import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

class SLAComposer:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.url = "https://api.anthropic.com/v1/messages"

    def structure_task(self, user_prompt):
        print(f"🤖 Claude is analyzing: '{user_prompt}'...")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 512,
            "messages": [
                {"role": "user", "content": f"Convert this into a JSON SLA spec: {user_prompt}. Return ONLY JSON with fields: title, description, reward_usdt, and success_criteria."}
            ]
        }

        try:
            response = requests.post(self.url, headers=headers, json=data)
            result = response.json()
            # Extract the JSON from Claude's response
            spec = json.loads(result['content'][0]['text'])
            return spec
        except Exception as e:
            return {"error": str(e), "fallback": "Check API Key in .env"}

if __name__ == "__main__":
    composer = SLAComposer()
    sample_task = "Write a high-quality poem about the X Layer blockchain's speed. Pay 5 USDT."
    structured_json = composer.structure_task(sample_task)
    print("\n✅ STRUCTURED SLA SPECIFICATION:")
    print(json.dumps(structured_json, indent=4))
