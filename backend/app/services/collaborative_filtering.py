import numpy as np
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from scipy.sparse.linalg import svds
from sklearn.metrics.pairwise import cosine_similarity

from app.db.mongodb import (
    news_collection,
    user_collection,
    user_interactions_collection
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollaborativeFilteringService:
    """Service for collaborative filtering-based recommendation"""

    def __init__(self):
        pass

    def build_user_item_matrix(self, days: int = 90, min_interactions: int = 3) -> Tuple[List[str], List[str], np.ndarray]:
        """Build user-item interaction matrix

        Returns:
            Tuple[List[str], List[str], np.ndarray]: User IDs, Item IDs, and interaction matrix
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get interactions from the last X days
        interactions = list(user_interactions_collection.find({
            "timestamp": {"$gte": start_date}
        }))

        if not interactions:
            logger.warning("No interactions found for building user-item matrix")
            return [], [], np.array([])

        # Count interactions per user
        user_counts = {}
        for interaction in interactions:
            user_id = interaction["user_id"]
            user_counts[user_id] = user_counts.get(user_id, 0) + 1

        # Filter users with sufficient interactions
        active_users = [user_id for user_id, count in user_counts.items() if count >= min_interactions]
        if not active_users:
            logger.warning(f"No users with at least {min_interactions} interactions")
            return [], [], np.array([])

        # Get all news IDs from interactions
        news_ids = set()
        for interaction in interactions:
            news_ids.add(interaction["news_id"])
        news_ids = sorted(list(news_ids))

        # Create mappings
        user_to_idx = {user_id: i for i, user_id in enumerate(active_users)}
        item_to_idx = {item_id: i for i, item_id in enumerate(news_ids)}

        # Initialize matrix
        matrix = np.zeros((len(active_users), len(news_ids)))

        # Interaction type weights
        interaction_weights = {
            "view": 0.5,
            "click": 1.0,
            "read": 2.0,
            "like": 3.0,
            "share": 4.0,
            "comment": 3.0,
            "save": 2.5
        }

        # Fill the matrix with interaction scores
        for interaction in interactions:
            user_id = interaction["user_id"]
            news_id = interaction["news_id"]

            # Skip if user or item not in our filtered set
            if user_id not in user_to_idx or news_id not in item_to_idx:
                continue

            user_idx = user_to_idx[user_id]
            item_idx = item_to_idx[news_id]

            # Get interaction weight
            interaction_type = interaction.get("interaction_type", "click")
            weight = interaction_weights.get(interaction_type, 1.0)

            # Apply advanced weighting if available
            if "dwell_time_seconds" in interaction.get("metadata", {}):
                dwell_time = interaction["metadata"]["dwell_time_seconds"]
                # Scale by dwell time: longer time means more interest
                if dwell_time > 300:  # More than 5 minutes
                    weight *= 2.0
                elif dwell_time > 120:  # More than 2 minutes
                    weight *= 1.5
                elif dwell_time > 60:  # More than 1 minute
                    weight *= 1.2

            # Update matrix (use max if multiple interactions)
            matrix[user_idx, item_idx] = max(matrix[user_idx, item_idx], weight)

        return active_users, news_ids, matrix

    def apply_svd(self, matrix: np.ndarray, k: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Apply Singular Value Decomposition to the user-item matrix

        Args:
            matrix: User-item interaction matrix
            k: Number of latent factors

        Returns:
            Tuple[np.ndarray, np.ndarray, np.ndarray]: U, sigma, Vt matrices
        """
        # Handle empty or too small matrices
        if matrix.size == 0 or min(matrix.shape) < 2:
            logger.warning("Matrix too small for SVD")
            return np.array([]), np.array([]), np.array([])

        # Center the matrix (subtract mean)
        matrix_mean = np.mean(matrix, axis=1).reshape(-1, 1)
        matrix_centered = matrix - matrix_mean

        # Apply SVD
        try:
            u, sigma, vt = svds(matrix_centered, k=min(k, min(matrix.shape) - 1))
            # Sort by singular values (descending)
            idx = np.argsort(sigma)[::-1]
            sigma = sigma[idx]
            u = u[:, idx]
            vt = vt[idx, :]
            return u, sigma, vt
        except Exception as e:
            logger.error(f"SVD failed: {e}")
            return np.array([]), np.array([]), np.array([])

    def predict_ratings(self, u: np.ndarray, sigma: np.ndarray, vt: np.ndarray, user_means: np.ndarray) -> np.ndarray:
        """Predict ratings using the SVD components

        Args:
            u: User matrix from SVD
            sigma: Singular values from SVD
            vt: Item matrix from SVD
            user_means: Mean rating for each user

        Returns:
            np.ndarray: Predicted ratings matrix
        """
        if u.size == 0 or sigma.size == 0 or vt.size == 0:
            return np.array([])

        # Diagonal matrix of singular values
        sigma_diag = np.diag(sigma)

        # Predict ratings
        pred = np.dot(np.dot(u, sigma_diag), vt)

        # Add back the mean
        pred_ratings = pred + user_means

        # Ensure non-negative ratings
        pred_ratings[pred_ratings < 0] = 0

        return pred_ratings

    def get_recommendations_for_user(self, user_id: str, limit: int = 10) -> List[str]:
        """Get collaborative filtering recommendations for a user

        Args:
            user_id: User ID
            limit: Max number of recommendations

        Returns:
            List[str]: List of recommended news IDs
        """
        # Build the user-item matrix
        user_ids, news_ids, matrix = self.build_user_item_matrix()

        # Check if user is in the matrix
        if user_id not in user_ids:
            logger.warning(f"User {user_id} not found in interaction matrix")
            return self._get_fallback_recommendations(user_id, limit)

        # Get user index
        user_idx = user_ids.index(user_id)

        # Apply SVD
        k = min(20, min(matrix.shape) - 1) if min(matrix.shape) > 1 else 1
        u, sigma, vt = self.apply_svd(matrix, k=k)

        if u.size == 0 or sigma.size == 0 or vt.size == 0:
            logger.warning("SVD failed, using fallback recommendations")
            return self._get_fallback_recommendations(user_id, limit)

        # Calculate mean ratings per user
        user_means = np.mean(matrix, axis=1).reshape(-1, 1)

        # Predict ratings
        predicted_ratings = self.predict_ratings(u, sigma, vt, user_means)

        # Get user's predicted ratings
        user_ratings = predicted_ratings[user_idx]

        # Get already interacted items
        interacted_items = set()
        for i, rating in enumerate(matrix[user_idx]):
            if rating > 0:
                interacted_items.add(i)

        # Get top rated items that user hasn't interacted with
        item_scores = [(i, score) for i, score in enumerate(user_ratings) if i not in interacted_items]
        item_scores.sort(key=lambda x: x[1], reverse=True)

        # Get top N items
        top_items = item_scores[:limit]

        # Convert item indices to news IDs
        recommended_news_ids = [news_ids[item_idx] for item_idx, _ in top_items]

        return recommended_news_ids

    def get_similar_users(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar users based on interaction patterns

        Args:
            user_id: User ID
            limit: Max number of similar users

        Returns:
            List[Dict[str, Any]]: List of similar users with similarity scores
        """
        # Build the user-item matrix
        user_ids, news_ids, matrix = self.build_user_item_matrix()

        # Check if user is in the matrix
        if user_id not in user_ids:
            logger.warning(f"User {user_id} not found in interaction matrix")
            return []

        # Get user index
        user_idx = user_ids.index(user_id)

        # Calculate cosine similarity between users
        user_similarities = cosine_similarity([matrix[user_idx]], matrix)[0]

        # Sort users by similarity (excluding the user itself)
        similar_indices = np.argsort(user_similarities)[::-1]
        similar_indices = [idx for idx in similar_indices if idx != user_idx and user_similarities[idx] > 0][:limit]

        # Create result
        similar_users = []
        for idx in similar_indices:
            similar_user_id = user_ids[idx]
            similarity = user_similarities[idx]
            similar_users.append({
                "user_id": similar_user_id,
                "similarity_score": float(similarity)
            })

        return similar_users

    def _get_fallback_recommendations(self, user_id: str, limit: int) -> List[str]:
        """Get fallback recommendations for a user (popular or trending items)

        Args:
            user_id: User ID
            limit: Max number of recommendations

        Returns:
            List[str]: List of recommended news IDs
        """
        # Get user's historical interactions
        user_interactions = list(user_interactions_collection.find({
            "user_id": user_id
        }).sort("timestamp", -1).limit(50))

        interacted_news_ids = set()
        topics = []
        categories = []

        # Extract news IDs and collect categories/topics from user history
        for interaction in user_interactions:
            news_id = interaction["news_id"]
            interacted_news_ids.add(news_id)

            # Try to get the news details
            news = news_collection.find_one({"_id": news_id})
            if news:
                categories.extend(news.get("categories", []))
                topics.extend(news.get("keywords", []))

        # Find news with similar categories/topics
        query = {}
        if categories:
            # Count categories to find most frequent
            category_counts = {}
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1

            # Get top 3 categories
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            if top_categories:
                query["categories"] = {"$in": [cat for cat, _ in top_categories]}

        # Exclude already interacted news
        if interacted_news_ids:
            query["_id"] = {"$nin": list(interacted_news_ids)}

        # Get recent news that match categories
        recent_news = list(news_collection.find(query).sort("published_date", -1).limit(limit * 2))

        # If not enough news with categories, fall back to most recent
        if len(recent_news) < limit:
            query = {"_id": {"$nin": list(interacted_news_ids)}} if interacted_news_ids else {}
            recent_news = list(news_collection.find(query).sort("published_date", -1).limit(limit))

        # Extract news IDs
        news_ids = [news["_id"] for news in recent_news][:limit]

        return news_ids


# Helper function to get service instance
def get_collaborative_filtering_service() -> CollaborativeFilteringService:
    """Get collaborative filtering service instance"""
    return CollaborativeFilteringService()
