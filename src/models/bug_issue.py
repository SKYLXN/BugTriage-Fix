class BugIssue:
    def __init__(self, number, title, description, code_context=None):
        self.number = number
        self.title = title
        self.description = description
        self.code_context = code_context
