class CodygenError(Exception):
    def __init__(self, message: str | None = None):
        super().__init__(message)
        self.message = message


class CodygenUserError(CodygenError):
    """user-facing error. displays a nice error message"""

    ...


class GuildExistsError(CodygenError):
    """raised when trying to initialize an existing guild. should be ignored"""

    ...


class DefaultError(CodygenError): ...


class MisconfigurationError(CodygenError): ...


class MissingEnvironmentVariable(CodygenError): ...


class FormDecodeError(CodygenError): ...


class LastfmLoggedOutError(CodygenError):
    def __init__(self, message: str | None = None):
        super().__init__(message) if message else None
        self.message = message


class ModuleDisabledError(CodygenError): ...


class UnknownEmoteError(CodygenError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = f"Can't find/use emote '{message}' in config. Please make sure it exists and has a valid id."
