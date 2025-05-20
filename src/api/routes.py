import hmac
import hashlib
import os
from typing import Dict, Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from src.services.github_service import (
    validate_signature,
    post_comment_on_issue,
    create_branch_and_pr,
)
from src.services.openai_service import run_bugtriage_agent

router = APIRouter(tags=["github"])

# ──────────────────────────────────────────────────────────────────────────
@router.post("/github", status_code=status.HTTP_204_NO_CONTENT)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
):
    """
    Point d'entrée unique pour tous les webhooks GitHub.
    * Pour le PoC, on traite uniquement `issues` → action `opened`.
    * Authentification : HMAC SHA-256 via le secret GitHub.
    """
    body: bytes = await request.body()

    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if secret is None:
        raise RuntimeError("GITHUB_WEBHOOK_SECRET not set")

    if not validate_signature(body, x_hub_signature_256, secret):
        raise HTTPException(status_code=401, detail="Bad signature")

    if x_github_event != "issues":
        return

    payload: Dict[str, Any] = await request.json()
    action = payload.get("action")
    if action != "opened":
        return

    issue = payload["issue"]
    repo = payload["repository"]

    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    issue_number = issue["number"]
    title = issue["title"]
    body_text = issue["body"] or ""

    # 1) Appelle Azure OpenAI pour analyser / proposer un patch
    suggestion = run_bugtriage_agent(
        title=title,
        description=body_text,
        repository_full_name=f"{owner}/{repo_name}",
        issue_number=issue_number,
    )

    # Extraire le diff du markdown généré par l’IA
    import re
    diff_match = re.search(r"```diff(.*?)```", suggestion, re.DOTALL)
    patch_diff = diff_match.group(1).strip() if diff_match else None

    if patch_diff:
        pr_url = await create_branch_and_pr(
            owner=owner,
            repo=repo_name,
            base_branch="Bug130",
            patch_diff=patch_diff,
            issue_number=issue_number,
            suggestion=suggestion,
        )
        # Commenter sur l’issue avec le lien PR
        await post_comment_on_issue(
            owner=owner,
            repo=repo_name,
            issue_number=issue_number,
            comment_text=f"Une proposition de correction a été soumise en pull request : {pr_url}",
        )
    else:
        # fallback : commentaire classique
        await post_comment_on_issue(
            owner=owner,
            repo=repo_name,
            issue_number=issue_number,
            comment_text=suggestion,
        )