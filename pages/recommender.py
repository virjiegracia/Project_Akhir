"""Alur rekomendasi: kandidat -> skor -> urut (merge sort) -> Top-N."""
from tunematch.pages.algorithms import merge_sort, jaccard, popularity_norm, score_song
from tunematch.pages.api_clients import APIError


def song_key(artist, title):
    return f"{artist}|{title}".lower().strip()


def build_recommendations(lfm, favorites, mood_tags, top_n=10,
                          similar_limit=30, tag_limit=20, pool_size=25):
    fav_keys = {song_key(f["artist"], f["title"]) for f in favorites}  # set
    cands = {}  # dictionary: key -> data kandidat (otomatis tanpa duplikat)
    user_tags = {t.lower() for t in mood_tags}

    def add(s, match, playcount=0):
        k = song_key(s["artist"], s["title"])
        if k in fav_keys:
            return
        c = cands.setdefault(k, {"key": k, "title": s["title"], "artist": s["artist"],
                                 "match": 0.0, "hits": 0, "playcount": 0})
        c["match"] = max(c["match"], match)
        c["playcount"] = max(c["playcount"], playcount)
        c["hits"] += 1

    for fav in favorites:
        user_tags.update(lfm.top_tags(fav["artist"], fav["title"], 5))
        for s in lfm.similar(fav["artist"], fav["title"], similar_limit):
            add(s, s["match"], s["playcount"])
    for tag in mood_tags[:3]:
        items = lfm.tag_top_tracks(tag, tag_limit)
        for rank, s in enumerate(items):
            add(s, 0.4 * (1 - rank / max(len(items), 1)))

    for c in cands.values():  # bonus jika muncul dari beberapa sumber
        c["match"] = min(1.0, c["match"] + 0.1 * (c["hits"] - 1))

    pool = merge_sort(list(cands.values()), key=lambda c: c["match"], reverse=True)[:pool_size]
    max_pop = max([c["playcount"] for c in pool] or [0])
    for c in pool:
        try:
            c["tags"] = lfm.top_tags(c["artist"], c["title"], 6)
        except APIError:
            c["tags"] = []
        sim = jaccard(c["tags"], user_tags)
        c["score"] = score_song(c["match"], sim, popularity_norm(c["playcount"], max_pop))
        c["genre"] = c["tags"][0] if c["tags"] else "lainnya"
        c["explanation"] = f"Direkomendasikan karena mirip dengan selera Anda (kemiripan {c['score']*100:.0f}%)."
    return merge_sort(pool, key=lambda c: c["score"], reverse=True)[:top_n]
