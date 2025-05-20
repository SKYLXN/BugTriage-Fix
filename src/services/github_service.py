import hmac
import hashlib
import os
import httpx
import base64
import json
import time
import re

GITHUB_API = "https://api.github.com"

def validate_signature(body: bytes, signature: str, secret: str) -> bool:
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    expected = f"sha256={sig}"
    return hmac.compare_digest(expected, signature)

async def post_comment_on_issue(owner: str, repo: str, issue_number: int, comment_text: str):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set")
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"body": comment_text}, headers=headers)
        resp.raise_for_status()

def parse_diff(patch_diff):
    """Parse a git diff to extract file paths and changes."""
    changes = []
    current_file = None
    chunk_lines = []
    
    for line in patch_diff.split('\n'):
        if line.startswith('--- a/') or line.startswith('+++ b/'):
            if line.startswith('+++ b/'):
                if current_file and chunk_lines:
                    changes.append({
                        'file': current_file,
                        'chunks': '\n'.join(chunk_lines)
                    })
                    chunk_lines = []
                
                current_file = line[6:] 
            continue
            
        if current_file:
            chunk_lines.append(line)
    
    if current_file and chunk_lines:
        changes.append({
            'file': current_file,
            'chunks': '\n'.join(chunk_lines)
        })
        
    return changes

def apply_patch_to_content(content, chunks):
    """Apply a patch chunk to file content."""
    lines = content.split('\n')
    
    chunk_pattern = r'@@ -(\d+),(\d+) \+(\d+),(\d+) @@'
    
    chunks_parts = re.split(r'(@@ .* @@)', chunks)
    
    current_position = 0
    
    for i in range(1, len(chunks_parts), 2):
        header = chunks_parts[i]
        content = chunks_parts[i+1] if i+1 < len(chunks_parts) else ""
        
        match = re.match(chunk_pattern, header)
        if match:
            start_line = int(match.group(3)) - 1  
            
            chunk_lines = content.strip().split('\n')
            modified_lines = []
            
            line_position = start_line
            
            for line in chunk_lines:
                if line.startswith('+'):
                    modified_lines.append(line[1:])
                    line_position += 1
                elif line.startswith('-'):
                    pass
                elif line.startswith(' '):
                    modified_lines.append(line[1:])
                    line_position += 1
            
            if start_line < len(lines):
                removed_count = 0
                for line in chunk_lines:
                    if line.startswith('-') or line.startswith(' '):
                        removed_count += 1
                
                lines = lines[:start_line] + modified_lines + lines[start_line + removed_count:]
    
    return '\n'.join(lines)

async def create_branch_and_pr(owner, repo, base_branch="master", patch_diff=None, issue_number=None, suggestion=None):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set")
    
    headers = {"Authorization": f"token {token}"}
    async with httpx.AsyncClient() as client:
        if not base_branch:
            repo_info = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers)
            repo_info.raise_for_status()
            base_branch = repo_info.json()["default_branch"]

        r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{base_branch}", headers=headers)
        r.raise_for_status()
        base_sha = r.json()["object"]["sha"]

        branch_name = f"bugfix/issue-{issue_number}-{int(time.time())}"
        ref_data = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
        r = await client.post(f"{GITHUB_API}/repos/{owner}/{repo}/git/refs", headers=headers, json=ref_data)
        r.raise_for_status()

        if patch_diff:
            r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/git/commits/{base_sha}", headers=headers)
            r.raise_for_status()
            base_tree_sha = r.json()["tree"]["sha"]
            
            changes = parse_diff(patch_diff)
            
            new_tree_items = []
 
            for change in changes:
                file_path = change['file']
                chunks = change['chunks']
                
                try:
                    r = await client.get(
                        f"{GITHUB_API}/repos/{owner}/{repo}/contents/{file_path}",
                        headers=headers,
                        params={"ref": base_branch}
                    )
                    r.raise_for_status()
                    file_data = r.json()
                    
                    encoded_content = file_data["content"]
                    current_content = base64.b64decode(encoded_content).decode('utf-8')
                    
                    new_content = apply_patch_to_content(current_content, chunks)
                    
                    blob_data = {
                        "content": new_content,
                        "encoding": "utf-8"
                    }
                    
                    r = await client.post(
                        f"{GITHUB_API}/repos/{owner}/{repo}/git/blobs", 
                        headers=headers, 
                        json=blob_data
                    )
                    r.raise_for_status()
                    blob_sha = r.json()["sha"]
                    
                    new_tree_items.append({
                        "path": file_path,
                        "mode": "100644", 
                        "type": "blob",
                        "sha": blob_sha
                    })
                except Exception as e:
                    error_note = f"Failed to apply changes to {file_path}: {str(e)}\n\nOriginal diff:\n```diff\n{chunks}\n```"
                    blob_data = {
                        "content": error_note,
                        "encoding": "utf-8"
                    }
                    r = await client.post(f"{GITHUB_API}/repos/{owner}/{repo}/git/blobs", headers=headers, json=blob_data)
                    r.raise_for_status()
                    blob_sha = r.json()["sha"]
                    
                    new_tree_items.append({
                        "path": f"patch_notes/{file_path.replace('/', '_')}_fix.md",
                        "mode": "100644", 
                        "type": "blob",
                        "sha": blob_sha
                    })
            
            summary = f"# Patch for Issue #{issue_number}\n\n{suggestion}\n\n## Files modified\n" + "\n".join([f"- {change['file']}" for change in changes])
            blob_data = {
                "content": summary,
                "encoding": "utf-8"
            }
            r = await client.post(f"{GITHUB_API}/repos/{owner}/{repo}/git/blobs", headers=headers, json=blob_data)
            r.raise_for_status()
            blob_sha = r.json()["sha"]
            
            new_tree_items.append({
                "path": f"bugfix_summary_{issue_number}.md",
                "mode": "100644", 
                "type": "blob",
                "sha": blob_sha
            })
            
            tree_data = {
                "base_tree": base_tree_sha,
                "tree": new_tree_items
            }
            r = await client.post(f"{GITHUB_API}/repos/{owner}/{repo}/git/trees", headers=headers, json=tree_data)
            r.raise_for_status()
            new_tree_sha = r.json()["sha"]
            
            commit_data = {
                "message": f"Fix for issue #{issue_number}",
                "tree": new_tree_sha,
                "parents": [base_sha]
            }
            r = await client.post(f"{GITHUB_API}/repos/{owner}/{repo}/git/commits", headers=headers, json=commit_data)
            r.raise_for_status()
            new_commit_sha = r.json()["sha"]
            
            r = await client.patch(
                f"{GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch_name}", 
                headers=headers,
                json={"sha": new_commit_sha}
            )
            r.raise_for_status()

        pr_data = {
            "title": f"Proposition de correction pour l'issue #{issue_number}",
            "head": branch_name,
            "base": base_branch,
            "body": suggestion + "\n\n_Patch généré automatiquement par BugTriage/Fix_"
        }
        r = await client.post(f"{GITHUB_API}/repos/{owner}/{repo}/pulls", headers=headers, json=pr_data)
        r.raise_for_status()
        return r.json()["html_url"]
