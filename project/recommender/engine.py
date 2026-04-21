import pandas as pd


class SubscriptionRecommender:

    def __init__(self, csv_path, region="IN"):
        self.df = pd.read_csv(csv_path)

        # Normalize text
        self.df["domain"] = self.df["domain"].str.lower()
        self.df["features"] = self.df["features"].fillna("").str.lower()
        self.df["regions"] = self.df["regions"].fillna("").str.upper()

        self.region = region.upper()

    def recommend(self, domain, budget, features, top_k=5):

        # Filter by domain
        df = self.df[self.df["domain"] == domain.lower()].copy()

        # Filter by region
        df = df[df["regions"].str.contains(self.region)]

        # Filter by budget
        if budget is not None:
            df = df[df["price_month"] <= budget]

        if df.empty:
            return []

        # Score calculation
        results = []

        for _, row in df.iterrows():
            item_features = row["features"].split()

            # Count matching features
            match_count = sum(1 for f in features if f.lower() in item_features)

            # Score = feature matches + rating
            score = match_count + float(row["rating"])

            reason = f"Matches {match_count} features and has rating {row['rating']}"

            results.append({
                "name": row["name"],
                "price_month": row["price_month"],
                "rating": row["rating"],
                "url": row["url"],
                "score": score,
                "reason": reason
            })

        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:top_k]