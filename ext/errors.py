class CodygenError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DefaultError(CodygenError):
    pass


class MisconfigurationError(CodygenError):
    pass


class MissingEnvironmentVariable(CodygenError):
    pass


# i will add more soon
