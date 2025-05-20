import os

def build_prompt(title, description, code_context=None, issue_number=None):
    prompt_template_path = os.path.join(
        os.path.dirname(__file__),
        "../config/prompts/bugfix_prompt.txt"
    )
    try:
        with open(prompt_template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception:
        # fallback
        template = (
            "You are BugTriage/Fix, an expert Java/Spring AI assistant.\n"
            "Analyze the following bug report, diagnose the probable cause, and if possible, suggest a patch as a diff.\n"
            "Issue #{number}: {title}\n\n"
            "Description:\n{description}\n\n"
            "Code context:\n{code_context}\n\n"
            "Reply in markdown, start with a diagnosis, then the patch (if applicable) in a diff block, then brief test recommendations."
        )
    prompt = template.format(
        number=issue_number or "",
        title=title or "",
        description=description or "",
        code_context=code_context or "[not provided]"
    )
    return prompt
