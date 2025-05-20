import os
from fastapi import APIRouter, Request, Header, HTTPException, status
from src.services.github_service import validate_signature, post_comment_on_issue
from src.services.openai_service import run_bugtriage_agent

router = APIRouter()

@router.post("/github", status_code=status.HTTP_204_NO_CONTENT)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256")
):
    body: bytes = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("GITHUB_WEBHOOK_SECRET not set")
    if not validate_signature(body, x_hub_signature_256, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    if x_github_event != "issues":
        return

    payload = await request.json()
    if payload.get("action") != "opened":
        return

    issue = payload["issue"]
    repo = payload["repository"]
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    issue_number = issue["number"]
    title = issue["title"]
    description = issue.get("body", "")

    suggestion = await run_bugtriage_agent(
        title=title,
        description=description,
        repository_full_name=f"{owner}/{repo_name}",
        issue_number=issue_number
    )

    await post_comment_on_issue(
        owner=owner,
        repo=repo_name,
        issue_number=issue_number,
        comment_text=suggestion,
    )
