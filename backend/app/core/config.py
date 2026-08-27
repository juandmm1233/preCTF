from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://prectf:prectf@localhost:5432/prectf"
    jwt_secret: str = "dev-jwt-secret"
    token_secret: str = "dev-token-secret"
    instructor_key: str = ""
    jwt_expire_hours: int = 12
    cors_origins: str = "http://localhost:5173,http://localhost"

    docker_host: str = "tcp://dockerproxy:2375"
    challenge_n1_image: str = ""
    challenge_network: str = "prectf_challenges"
    lab_base_domain: str = "localhost"
    lab_public_port: int = 8088
    lab_ttl_minutes: int = 45
    prectf_max_lab_sessions: int = 20
    lab_internal_port: int = 80
    traefik_dynamic_dir: str = "/traefik/dynamic"

    admin_email: str = ""
    admin_password: str = ""
    admin_code: str = "DOCENTE"
    admin_name: str = "Instructor preCTF"

    prectf_flag_n1: str = "FLAG{PRECTF_N1_SQLI}"
    prectf_flag_n2: str = "FLAG{PRECTF_N2_COOKIE}"
    prectf_flag_n3: str = "FLAG{PRECTF_N3_LFI}"
    prectf_flag_n4: str = "FLAG{PRECTF_N4_CONFIG}"
    prectf_flag_n5: str = "FLAG{PRECTF_N5_CMDI}"
    prectf_flag_n6: str = "FLAG{PRECTF_N6_HASH}"
    prectf_flag_n7: str = "FLAG{PRECTF_N7_UPLOAD}"
    prectf_flag_n8: str = "FLAG{PRECTF_N8_SSH}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def flag_for_level(self, order_index: int) -> str:
        mapping = {
            1: self.prectf_flag_n1,
            2: self.prectf_flag_n2,
            3: self.prectf_flag_n3,
            4: self.prectf_flag_n4,
            5: self.prectf_flag_n5,
            6: self.prectf_flag_n6,
            7: self.prectf_flag_n7,
            8: self.prectf_flag_n8,
        }
        return mapping[order_index]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
