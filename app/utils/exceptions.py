class AppError(Exception):
    """Base application error with HTTP mapping."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AliasAlreadyExistsError(AppError):
    def __init__(self, alias: str) -> None:
        super().__init__(
            message=f"Alias '{alias}' is already in use",
            status_code=409,
        )


class UrlMappingNotFoundError(AppError):
    def __init__(self, alias: str) -> None:
        super().__init__(
            message=f"Short URL '{alias}' not found",
            status_code=404,
        )


class AliasGenerationError(AppError):
    def __init__(self) -> None:
        super().__init__(
            message="Unable to generate a unique alias after multiple attempts",
            status_code=503,
        )
