import re
import logging
from dataclasses import dataclass
from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    passed: bool
    reason: str | None = None


class ChunkValidator:
    def __init__(self):
        settings = get_settings()
        self.min_length = settings.min_semantic_chunk_length if settings.semantic_chunking_enabled else settings.min_chunk_length
        self.min_alpha_ratio = settings.chunk_validation_min_alpha_ratio
        self.min_words = settings.chunk_validation_min_words

    def validate(self, chunk: dict) -> ValidationResult:
        text = chunk.get("text", "").strip()
        if not text:
            return ValidationResult(False, "empty_text")

        if len(text) < self.min_length:
            return ValidationResult(False, f"too_short ({len(text)} < {self.min_length})")

        if _is_isolated_number_block(text):
            return ValidationResult(False, "isolated_number_block")

        alpha_ratio = _alpha_ratio(text)
        if alpha_ratio < self.min_alpha_ratio:
            return ValidationResult(False, f"low_alpha_ratio ({alpha_ratio:.2f} < {self.min_alpha_ratio})")

        word_count = len(text.split())
        if word_count < self.min_words:
            return ValidationResult(False, f"too_few_words ({word_count} < {self.min_words})")

        return ValidationResult(True)

    def filter_chunks(self, chunks: list[dict]) -> tuple[list[dict], int]:
        valid: list[dict] = []
        rejected = 0
        for chunk in chunks:
            result = self.validate(chunk)
            if result.passed:
                valid.append(chunk)
            else:
                rejected += 1
                logger.debug(f"Rejected chunk page={chunk.get('page')}: {result.reason}")
        return valid, rejected


def _alpha_ratio(text: str) -> float:
    alpha = len(re.findall(r"[a-zA-Z]", text))
    total = len(re.sub(r"\s", "", text))
    return alpha / max(total, 1)


def _is_isolated_number_block(text: str) -> bool:
    lines = text.strip().split("\n")
    number_lines = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d{1,4}$", stripped):
            number_lines += 1
    return number_lines >= 3 and number_lines / max(len(lines), 1) > 0.5


chunk_validator = ChunkValidator()
