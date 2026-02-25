from discord.ui import LayoutView, MediaGallery, Container, TextDisplay
from discord import MediaGalleryItem, File


class LevelGetLayout(LayoutView):
    def __init__(self, img_path: str, header: str | None) -> None:
        super().__init__()
        con = Container()
        if header:
            con.add_item(TextDisplay(header))
        con.add_item(MediaGallery(MediaGalleryItem(File(img_path))))
        self.add_item(con)
