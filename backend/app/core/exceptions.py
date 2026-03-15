from fastapi import HTTPException

class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class ParseError(AppError):
    pass

class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 404)

class LLMError(AppError):
    pass
