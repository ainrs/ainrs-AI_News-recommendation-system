import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.db.mongodb import (
    news_collection,
    user_collection,
    user_interactions_collection
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserAnalyticsService:
    """Service for analyzing user behavior and generating insights"""

    def __init__(self):
        pass

    def get_user_interaction_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get statistics about a user's interactions"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all interactions for the user within the time period
        interactions = list(user_interactions_collection.find({
            "user_id": user_id,
            "timestamp": {"$gte": start_date}
        }))

        if not interactions:
            return {
                "total_interactions": 0,
                "interaction_types": {},
                "categories": {},
                "sources": {},
                "avg_trust_score": None,
                "avg_sentiment_score": None
            }

        # Count interaction types
        interaction_types = {}
        for interaction in interactions:
            interaction_type = interaction.get("interaction_type", "unknown")
            interaction_types[interaction_type] = interaction_types.get(interaction_type, 0) + 1

        # Get news IDs from interactions
        news_ids = [interaction["news_id"] for interaction in interactions]

        # Get news details
        news_items = list(news_collection.find({"_id": {"$in": news_ids}}))

        # Count categories
        categories = {}
        for news in news_items:
            for category in news.get("categories", []):
                categories[category] = categories.get(category, 0) + 1

        # Count sources
        sources = {}
        for news in news_items:
            source = news.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        # Calculate average trust and sentiment scores
        trust_scores = [news.get("trust_score") for news in news_items if news.get("trust_score") is not None]
        sentiment_scores = [news.get("sentiment_score") for news in news_items if news.get("sentiment_score") is not None]

        avg_trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else None
        avg_sentiment_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None

        return {
            "total_interactions": len(interactions),
            "interaction_types": interaction_types,
            "categories": categories,
            "sources": sources,
            "avg_trust_score": avg_trust_score,
            "avg_sentiment_score": avg_sentiment_score
        }

    def get_user_engagement_score(self, user_id: str, days: int = 30) -> float:
        """Calculate an engagement score for a user based on interaction frequency and type"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all interactions for the user within the time period
        interactions = list(user_interactions_collection.find({
            "user_id": user_id,
            "timestamp": {"$gte": start_date}
        }))

        if not interactions:
            return 0.0

        # Define weights for different interaction types
        interaction_weights = {
            "view": 0.5,  # Just viewing a headline
            "click": 1.0,  # Clicking to read
            "read": 2.0,   # Reading the article (longer dwell time)
            "like": 3.0,   # Explicitly liking
            "share": 4.0,  # Sharing with others
            "comment": 3.5 # Commenting on the article
        }

        # Calculate weighted score
        total_score = 0.0
        for interaction in interactions:
            interaction_type = interaction.get("interaction_type", "unknown")
            weight = interaction_weights.get(interaction_type, 1.0)

            # Add recency factor - more recent interactions get higher weight
            days_ago = (datetime.utcnow() - interaction["timestamp"]).days
            recency_factor = max(0.1, 1.0 - (days_ago / days))

            # Add dwell time factor if available
            dwell_time_factor = 1.0
            if interaction_type == "read" and "dwell_time_seconds" in interaction.get("metadata", {}):
                dwell_seconds = interaction["metadata"]["dwell_time_seconds"]
                # Scale dwell time: 0-30s: 1x, 30-60s: 2x, 60-120s: 3x, 120+: 4x
                if dwell_seconds >= 120:
                    dwell_time_factor = 4.0
                elif dwell_seconds >= 60:
                    dwell_time_factor = 3.0
                elif dwell_seconds >= 30:
                    dwell_time_factor = 2.0

            # Calculate final score for this interaction
            interaction_score = weight * recency_factor * dwell_time_factor
            total_score += interaction_score

        # Normalize the score (0-100 scale)
        normalized_score = min(100, total_score)

        return normalized_score

    def build_user_item_matrix(self, days: int = 90, min_interactions: int = 5) -> Tuple[List[str], List[str], np.ndarray]:
        """Build a user-item interaction matrix for collaborative filtering

        Returns:
            tuple: (user_ids, news_ids, interaction_matrix)
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all interactions within the time period
        interactions = list(user_interactions_collection.find({
            "timestamp": {"$gte": start_date}
        }))

        if not interactions:
            return [], [], np.array([])

        # Count interactions per user to filter out users with too few interactions
        user_interaction_counts = {}
        for interaction in interactions:
            user_id = interaction["user_id"]
            user_interaction_counts[user_id] = user_interaction_counts.get(user_id, 0) + 1

        # Filter users with enough interactions
        active_users = [user_id for user_id, count in user_interaction_counts.items()
                        if count >= min_interactions]

        if not active_users:
            return [], [], np.array([])

        # Filter interactions to only include active users
        filtered_interactions = [interaction for interaction in interactions
                                if interaction["user_id"] in active_users]

        # Get unique users and news items
        user_ids = sorted(list(set(interaction["user_id"] for interaction in filtered_interactions)))
        news_ids = sorted(list(set(interaction["news_id"] for interaction in filtered_interactions)))

        # Create mapping from ID to index
        user_to_index = {user_id: i for i, user_id in enumerate(user_ids)}
        news_to_index = {news_id: i for i, news_id in enumerate(news_ids)}

        # Initialize matrix
        matrix = np.zeros((len(user_ids), len(news_ids)))

        # Define weights for different interaction types
        interaction_weights = {
            "view": 0.5,
            "click": 1.0,
            "read": 2.0,
            "like": 3.0,
            "share": 4.0,
            "comment": 3.5
        }

        # Fill the matrix
        for interaction in filtered_interactions:
            user_idx = user_to_index[interaction["user_id"]]
            news_idx = news_to_index[interaction["news_id"]]

            # Get the weight for this interaction type
            interaction_type = interaction.get("interaction_type", "click")
            weight = interaction_weights.get(interaction_type, 1.0)

            # Update the matrix value (use higher value if there are multiple interactions)
            matrix[user_idx, news_idx] = max(matrix[user_idx, news_idx], weight)

        return user_ids, news_ids, matrix

    def get_similar_users(self, user_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Find similar users based on interaction patterns"""
        # Build the user-item matrix
        user_ids, news_ids, matrix = self.build_user_item_matrix()

        if not user_ids or user_id not in user_ids:
            return []

        # Get the user's index
        user_idx = user_ids.index(user_id)

        # Calculate cosine similarity
        user_similarities = cosine_similarity([matrix[user_idx]], matrix)[0]

        # Sort by similarity (excluding the user itself)
        similar_user_indices = np.argsort(user_similarities)[::-1]
        similar_user_indices = [idx for idx in similar_user_indices if idx != user_idx][:top_n]

        # Create result
        similar_users = []
        for idx in similar_user_indices:
            similar_user_id = user_ids[idx]
            similarity_score = user_similarities[idx]

            if similarity_score > 0:  # Only include users with some similarity
                similar_users.append({
                    "user_id": similar_user_id,
                    "similarity_score": similarity_score
                })

        return similar_users

    def get_user_category_preferences(self, user_id: str, days: int = 90) -> Dict[str, float]:
        """Calculate a user's category preferences based on interactions"""
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get all interactions for the user within the time period
        interactions = list(user_interactions_collection.find({
            "user_id": user_id,
            "timestamp": {"$gte": start_date}
        }))

        if not interactions:
            return {}

        # Get news IDs from interactions
        news_ids = [interaction["news_id"] for interaction in interactions]

        # Get news details
        news_items = list(news_collection.find({"_id": {"$in": news_ids}}))

        # Count categories
        category_counts = {}
        for news in news_items:
            for category in news.get("categories", []):
                category_counts[category] = category_counts.get(category, 0) + 1

        # Calculate preferences (normalize to sum to 1)
        total_count = sum(category_counts.values())
        category_preferences = {
            category: count / total_count
            for category, count in category_counts.items()
        }

        return category_preferences

    def get_collaborative_filtering_recommendations(self, user_id: str, limit: int = 10) -> List[str]:
        """Get collaborative filtering-based recommendations for a user"""
        # Find similar users
        similar_users = self.get_similar_users(user_id)

        if not similar_users:
            return []

        # Get user's recently viewed news
        recent_interactions = list(user_interactions_collection.find({
            "user_id": user_id
        }).sort("timestamp", -1).limit(50))

        viewed_news_ids = set(interaction["news_id"] for interaction in recent_interactions)

        # Get news that similar users have interacted with
        recommended_news = {}

        for similar_user in similar_users:
            similar_user_id = similar_user["user_id"]
            similarity_score = similar_user["similarity_score"]

            # Get this user's interactions
            user_interactions = list(user_interactions_collection.find({
                "user_id": similar_user_id
            }).sort("timestamp", -1).limit(20))

            for interaction in user_interactions:
                news_id = interaction["news_id"]

                # Skip already viewed news
                if news_id in viewed_news_ids:
                    continue

                # Calculate recommendation score
                interaction_type = interaction.get("interaction_type", "click")
                base_score = 1.0
                if interaction_type == "like":
                    base_score = 2.0
                elif interaction_type == "share":
                    base_score = 3.0

                # Weight by user similarity
                weighted_score = base_score * similarity_score

                # Add to recommendations
                if news_id in recommended_news:
                    recommended_news[news_id] += weighted_score
                else:
                    recommended_news[news_id] = weighted_score

        # Sort by score
        sorted_recommendations = sorted(
            recommended_news.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Return top N news IDs
        return [news_id for news_id, _ in sorted_recommendations[:limit]]


# Helper function to get service instance
def get_user_analytics_service() -> UserAnalyticsService:
    """Get user analytics service instance"""
    return UserAnalyticsService()
