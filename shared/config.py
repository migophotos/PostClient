from dataclasses import dataclass
import private.tokens as SECRET


@dataclass
class Config:
    owner_name: str = SECRET.APP_OWNER
    app_title: str = SECRET.APP_TITLE
    app_name: str = SECRET.APP_NAME
    api_id: int = SECRET.API_ID
    api_hash: str = SECRET.API_HASH

    app_channel_id: int = SECRET.APP_CHANNEL_ID
    app_channel_name: str = SECRET.APP_CHANNEL_NAME

    database: str = SECRET.APP_DATABASE

    owner_id: int = SECRET.APP_OWNER_ID

    enable_forbidden_content = False
