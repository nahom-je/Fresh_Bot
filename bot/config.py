from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    database_url: str
    storage_channel_id: int
    admin_chat_id: int
    admin_ids: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""

    force_sub_channel_id: int | None = None
    force_sub_channel_link: str | None = None

    cbe_account: str = "1000531330041"
    telebirr_number: str = "0974715586"
    account_holder: str = "Bereket Alemayehu"
    account_holder_cbe: str = "Bereket Alemayehu"
    account_holder_telebirr: str = "Walala shumi"
    price_etb: int = 150
    
    university_name: str = "Addis Ababa University"
    courses: str = "MATH101:Applied Mathematics I, PHYS101:General Physics, ENGL101:Communicative English Skills I, GEOG101:Geography of Ethiopia and the Horn, LOGI101:Logic and Critical Thinking, PSYC101:General Psychology"

    @property
    def courses_dict(self) -> dict[str, str]:
        res = {}
        for part in self.courses.split(","):
            part = part.strip()
            if not part: continue
            if ":" in part:
                code, name = part.split(":", 1)
                res[code.strip().upper()] = name.strip()
            else:
                res[part.upper()] = part.upper()
        return res

    @field_validator("force_sub_channel_id", mode="before")
    @classmethod
    def _parse_optional_int(cls, v: any) -> int | None:
        if v == "" or v is None:
            return None
        return int(v)

    @field_validator("force_sub_channel_link", mode="before")
    @classmethod
    def _parse_optional_str(cls, v: any) -> str | None:
        if not v:
            return None
        return str(v)

    @field_validator("database_url")
    @classmethod
    def _asyncpg_driver(cls, v: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix):]
        return v

    @property
    def admin_id_set(self) -> set[int]:
        return {int(x) for x in self.admin_ids.replace(" ", "").split(",") if x}


settings = Settings()
