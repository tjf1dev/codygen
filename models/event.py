class Event:
    def __init__(self, name: str, category: int, id: str, category_name: str):
        self.name = name
        self.id = id
        self.category = category
        self.category_name = category_name

    def __repr__(self):
        return f"Event(name={self.name!r}, id={self.id!r}, category={self.category!r} category_name={self.category_name!r})"
