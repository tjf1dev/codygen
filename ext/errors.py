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

class UnknownEmoteError(CodygenError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = f"Can't find/use emote '{message}' in config. Please make sure it exists and has a valid id."
