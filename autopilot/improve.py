"""Close the loop: analytics -> which traits retain best -> bias the next video (explore/exploit)."""
import statistics


def rank_traits(records, trait, min_samples=3):
    groups = {}
    for r in records:
        v, pct = (r.get("variety") or {}).get(trait), r.get("avg_view_pct")
        if v and pct is not None: groups.setdefault(v, []).append(pct)
    rows = [{"value": k, "n": len(v), "mean_view_pct": round(statistics.mean(v), 2)} for k, v in groups.items() if len(v) >= min_samples]
    return sorted(rows, key=lambda x: -x["mean_view_pct"])


def build_insights(records):
    return {"subgenre": rank_traits(records, "subgenre"), "structure": rank_traits(records, "structure"),
            "visual_style": rank_traits(records, "visual_style"), "samples": len([r for r in records if r.get("avg_view_pct") is not None])}


def pick_subgenre(subgenres, insights, rng, epsilon=0.3):
    ranked = [r["value"] for r in (insights or {}).get("subgenre", []) if r["value"] in subgenres]
    if ranked and rng.random() >= epsilon: return ranked[0]
    return rng.choice(subgenres)
