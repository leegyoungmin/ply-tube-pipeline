from typing import List

class Playlist:
    def __init__(self, title: str, video_id: str | None, informations: List[str] = []):
        self.title = title
        self.video_id = video_id
        self.informations = informations

    def __str__(self) -> str:
        return f"""
        Title : {self.title},
        Video Id :{self.video_id},
        INFORMATION: {self.informations}
        """

    def insert_information(self, info: str):
        self.informations.append(info)

    def convert_informations(self, infos: List[str]):
        self.informations = infos

    def to_json(self):
        return {
            "title": self.title,
            "video_id": self.video_id,
            "items": self.informations
        }