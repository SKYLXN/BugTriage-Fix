import os
from openai import AzureOpenAI
from src.services.prompt_service import build_prompt

endpoint = os.getenv("ENDPOINT_URL")
deployment = os.getenv("DEPLOYMENT_NAME")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2025-01-01-preview",
)

def run_bugtriage_agent(title, description, repository_full_name, issue_number):
    prompt = build_prompt(title, description, issue_number=issue_number)
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": "You are a senior Java/Spring developer."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800,
        temperature=0.5,
        top_p=1
    )
    return response.choices[0].message.content
