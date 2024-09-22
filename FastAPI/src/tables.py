from sqlalchemy import Table, Column, Integer, String, MetaData, TIMESTAMP, func

metadata = MetaData()

music = Table(
    "music",
    metadata,
    Column("music_id", Integer, primary_key=True),
    Column("play_id", String(50)),
    Column("music_info", String(255)),
    Column("feature_music_info", String(255)),
    Column("created_at", TIMESTAMP, default=func.now())
)


playlist = Table(
    "playlist",
    metadata,
    Column("play_id", String(50), primary_key=True),
    Column("title", String(255)),
    Column("music_info", TIMESTAMP, default=func.now()),
)