class CodygenError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class CodygenUserError(CodygenError):
    """user-facing error. displays a nice error message"""

    pass


class DefaultError(CodygenError):
    pass


class MisconfigurationError(CodygenError):
    pass


class MissingEnvironmentVariable(CodygenError):
    pass


class LastfmLoggedOutError(CodygenError):
    def __init__(self, message: str | None = None):
        super().__init__(message) if message else None
        self.message = message


class ModuleDisabledError(CodygenError):
    pass
