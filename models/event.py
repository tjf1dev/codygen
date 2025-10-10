from typing import Optional


class Event:
    def __init__(
        self,
        name: str,
        category: int,
        id: str,
        category_name: str,
        channel: Optional[str] = None,
    ):
        self.name = name
        self.id = id
        self.category = category
        self.category_name = category_name
        self.channel = channel

    def __repr__(self):
        return (
            f"Event(name={self.name!r}, id={self.id!r}, category={self.category!r}, "
            f"category_name={self.category_name!r}, channel={self.channel!r})"
        )

    def to_dict(self) -> dict:
        data = {
            "name": self.name,
            "id": self.id,
            "category": self.category,
            "category_name": self.category_name,
        }
        if self.channel is not None:
            data["channel"] = self.channel
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        return cls(
            name=data["name"],
            category=data["category"],
            id=data["id"],
            category_name=data["category_name"],
            channel=data.get("channel"),
        )
