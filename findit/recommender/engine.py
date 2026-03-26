"""Recommendation engine: thin wrapper around MatchingService.

This module is kept for backward compatibility. The actual logic
now lives in findit.services.matching_service.
"""

from __future__ import annotations

import logging

from findit.config import settings
from findit.db import Database
from findit.services.matching_service import MatchingService

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Delegates to MatchingService for all recommendation logic."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database(settings.db_path)
        self.matching = MatchingService(db=self.db)

    def get_daily_matches(self, user_id: int, count: int | None = None) -> list[dict]:
        """Get the daily batch of matches for a user."""
        return self.matching._select_daily_matches(user_id, count)

    def process_pipeline_for_user(self, user: dict) -> list[dict]:
        """Full pipeline for a user: filter + score + match."""
        return self.matching.generate_matches(user)
