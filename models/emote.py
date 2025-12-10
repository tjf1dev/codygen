from discord import PartialEmoji


class Emote:
    def __init__(self, name: str, id: int, animated: bool):
        self.name = name
        self.id = id
        self.animated = animated

    def __str__(self):
        return f"<{'a' if self.animated else ''}:{self.name}:{self.id}>"

    def string(self):
        return self.__str__()

    def __repr__(self):
        return str(self)

    def PartialEmoji(self):
        return PartialEmoji(name=self.name, id=self.id, animated=self.animated)
