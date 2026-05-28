import json
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


class RecommendationService:
    def analyze_batch(self, documents: list, storage_service) -> str:
        file_types = set()
        total_size = 0
        for doc in documents:
            file_types.add(doc.file_type)
            total_size += doc.size_bytes

        if "csv" in file_types or total_size < 500_000:
            return "vector"

        return "vector"


recommendation_service = RecommendationService()
