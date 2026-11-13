"""Tests for sync_reviews.py. Run: python3 scripts/test_sync_reviews.py (no network, no secrets)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import sync_reviews as sr  # noqa: E402

ENV = {"GBP_ACCOUNT_ID": "1", "GBP_LOCATION_ID": "2"}


def review(name, comment, stars="FIVE"):
    return {"reviewer": {"displayName": name}, "comment": comment, "starRating": stars}


class SyncReviews(unittest.TestCase):
    def test_follows_every_page(self):
        calls = []

        def get(url, token):
            calls.append(url)
            if "pageToken" not in url:
                return {"averageRating": 4.9, "totalReviewCount": 3, "reviews": [review("A", "one")], "nextPageToken": "x y"}
            return {"reviews": [review("B", "two")]}

        rating, count, reviews = sr.parse(sr.fetch_pages(ENV, "t", get))
        self.assertEqual((rating, count), (4.9, 3))
        self.assertEqual([r["author"] for r in reviews], ["A", "B"])
        self.assertEqual(len(calls), 2)
        self.assertIn("pageToken=x%20y", calls[1])

    def test_star_only_reviews_count_but_are_not_shown(self):
        pages = [{"averageRating": 5, "totalReviewCount": 2, "reviews": [review("A", "great"), review("B", "")]}]
        _, count, reviews = sr.parse(pages)
        self.assertEqual(count, 2)
        self.assertEqual(len(reviews), 1)

    def test_keeps_real_star_rating(self):
        pages = [{"averageRating": 4, "totalReviewCount": 1, "reviews": [review("A", "ok", "TWO")]}]
        self.assertEqual(sr.parse(pages)[2][0]["rating"], 2)

    def test_translated_review_keeps_original_words(self):
        text = "Great job\n\n(Translated by Google)\nGran trabajo"
        self.assertEqual(sr.clean_comment(text), "Great job")
        text = "(Translated by Google) Great job\n\n(Original)\nGran   trabajo"
        self.assertEqual(sr.clean_comment(text), "Gran trabajo")

    def test_empty_response_never_wipes_the_file(self):
        with self.assertRaises(ValueError):
            sr.merge({"reviews": [{"author": "A"}]}, None, None, [], "2026-01-01")
        with self.assertRaises(ValueError):
            sr.merge({"reviews": [{"author": "A"}]}, 5, 10, [], "2026-01-01")

    def test_no_change_means_no_rewrite(self):
        reviews = [{"author": "A", "rating": 5, "body": "x"}]
        current = {"rating": 5, "review_count": 1, "reviews": reviews, "synced": "old", "maps_uri": "u"}
        self.assertIsNone(sr.merge(current, 5, 1, reviews, "new"))

    def test_new_review_updates_and_keeps_other_fields(self):
        current = {"rating": 5, "review_count": 1, "reviews": [], "synced": "old", "maps_uri": "u"}
        reviews = [{"author": "A", "rating": 5, "body": "x"}]
        updated = sr.merge(current, 5, 2, reviews, "new")
        self.assertEqual(updated["review_count"], 2)
        self.assertEqual(updated["synced"], "new")
        self.assertEqual(updated["maps_uri"], "u")


if __name__ == "__main__":
    unittest.main()
