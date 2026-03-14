from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ACCESS_MINUTES: int = 30
    JWT_REFRESH_DAYS: int = 30
    JWT_ALG: str = "HS256"

    # SMTP / E-Mail
    SMTP_HOST: str = "smtp.oswald-it.ch"
    SMTP_PORT: int = 465
    SMTP_USER: str = "passwort@oswald-it.ch"
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Workplan <passwort@oswald-it.ch>"

    # Frontend URL für Reset-Links
    FRONTEND_URL: str = "https://workplan.oswald-it.ch"


settings = Settings()
