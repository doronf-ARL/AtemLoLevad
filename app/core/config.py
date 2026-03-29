from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Caregiver Support AI"
    database_url: str = "sqlite:///./caregiver_support.db"
    prompt_version: str = "v1"
    model_version: str = "deterministic-mvp"
    retrieval_version: str = "tag-overlap-v1"
    rule_set_version: str = "rules-v1"
    expert_review_mode: str = "manual_review_required"
    openai_api_key_env: str = "OPENAI_API_KEY"
    gemini_api_key_env: str = "GEMINI_API_KEY"
    base_dir: Path = Path(__file__).resolve().parents[2]


settings = Settings()
