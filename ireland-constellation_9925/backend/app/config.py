import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "your_project")
    BQ_DATASET: str = os.getenv("BQ_DATASET", "ireland_constellation")
    BQ_LOCATION: str = os.getenv("BQ_LOCATION", "europe-west1")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "your_project")
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "europe-west1")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()
