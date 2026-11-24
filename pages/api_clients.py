"""Klien API: Last.fm (data lagu), Deezer (cover/preview), Gemini (AI)."""
import json
import re
import requests


class APIError(Exception):
    pass


def _name(x):
    return x.get("name", "") if isinstance(x, dict) else str(x)


class LastFM:
    BASE = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, api_key, cache):
        self.api_key = api_key
        self.cache = cache  # dictionary sebagai cache hasil API

    def _get(self, **params):
        key = "lfm|" + json.dumps(params, sort_keys=True)
        if key in self.cache:
            return self.cache[key]
        if not self.api_key:
            raise APIError("LASTFM_API_KEY belum diisi.")
        params.update(api_key=self.api_key, format="json")
        try:
            r = requests.get(self.BASE, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            raise APIError(f"Gagal menghubungi Last.fm: {e}")
        if "error" in data:
            raise APIError(f"Last.fm: {data.get('message', 'error')}")
        self.cache[key] = data
        return data

    def search_tracks(self, query, limit=8):
        data = self._get(method="track.search", track=query, limit=limit)
        tracks = data.get("results", {}).get("trackmatches", {}).get("track", [])
        return [{"title": t["name"], "artist": _name(t["artist"])} for t in tracks]

    def similar(self, artist, title, limit=30):
        data = self._get(method="track.getsimilar", artist=artist, track=title,
                         limit=limit, autocorrect=1)
        out = []
        for t in data.get("similartracks", {}).get("track", []):
            out.append({"title": t["name"], "artist": _name(t["artist"]),
                        "match": float(t.get("match", 0) or 0),
                        "playcount": int(t.get("playcount", 0) or 0)})
        return out

    def top_tags(self, artist, title, n=6):
        data = self._get(method="track.gettoptags", artist=artist, track=title, autocorrect=1)
        tags = data.get("toptags", {}).get("tag", [])
        return [t["name"].lower() for t in tags[:n]]

    def tag_top_tracks(self, tag, limit=20):
        data = self._get(method="tag.gettoptracks", tag=tag, limit=limit)
        return [{"title": t["name"], "artist": _name(t["artist"])}
                for t in data.get("tracks", {}).get("track", [])]


class Deezer:
    def __init__(self, cache):
        self.cache = cache

    def lookup(self, artist, title):
        key = f"dz|{artist}|{title}".lower()
        if key in self.cache:
            return self.cache[key]
        info = {}
        try:
            r = requests.get("https://api.deezer.com/search", timeout=10,
                             params={"q": f'artist:"{artist}" track:"{title}"', "limit": 1})
            data = r.json().get("data", [])
            if data:
                info = {"cover": data[0]["album"].get("cover_medium"),
                        "preview": data[0].get("preview")}
        except Exception:
            info = {}
        self.cache[key] = info
        return info


class GeminiAI:
    def __init__(self, api_key, model="gemini-2.5-flash"):
        self.api_key, self.model, self.last_error = api_key, model, None

    @property
    def enabled(self):
        return bool(self.api_key)

    def _ask_json(self, prompt):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        resp = client.models.generate_content(
            model=self.model, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"))
        text = re.sub(r"^```(?:json)?|```$", "", resp.text.strip(), flags=re.M).strip()
        return json.loads(text)

    def mood_to_tags(self, mood):
        """Ubah deskripsi mood/aktivitas menjadi tag bergaya Last.fm."""
        fallback = [w for w in re.findall(r"[a-z]+", mood.lower()) if len(w) > 3][:3]
        if not self.enabled:
            return fallback
        prompt = ('Ubah deskripsi suasana/aktivitas pendengar musik berikut menjadi 3 sampai 5 '
                  'tag musik bahasa Inggris huruf kecil yang lazim dipakai di Last.fm '
                  '(genre, mood, atau tempo). Balas HANYA JSON: {"tags": ["..."]}.\n'
                  f'Deskripsi: "{mood}"')
        try:
            tags = self._ask_json(prompt).get("tags", [])
            return [str(t).lower().strip() for t in tags][:5] or fallback
        except Exception as e:
            self.last_error = str(e)
            return fallback

    def explain(self, mood, favorites, recs):
        """Kembalikan (ringkasan selera, daftar penjelasan per lagu)."""
        default = [r["explanation"] for r in recs]
        if not self.enabled or not recs:
            return "", default
        favs = "; ".join(f"{f['title']} - {f['artist']}" for f in favorites[:10]) or "(tidak ada)"
        lines = "\n".join(f"{i+1}. {r['title']} - {r['artist']} (tag: {', '.join(r['tags'][:4])}; "
                          f"kemiripan {r['score']*100:.0f}%)" for i, r in enumerate(recs))
        prompt = ("Kamu asisten rekomendasi musik. Tulis dalam Bahasa Indonesia.\n"
                  f"Mood/aktivitas pengguna: {mood or '(tidak disebutkan)'}\n"
                  f"Lagu favorit: {favs}\nRekomendasi:\n{lines}\n\n"
                  'Balas HANYA JSON: {"summary": "ringkasan selera musik pengguna (2 kalimat)", '
                  f'"explanations": [tepat {len(recs)} string, masing-masing 1-2 kalimat alasan lagu ke-i cocok]}}')
        try:
            data = self._ask_json(prompt)
            ex = data.get("explanations", [])
            merged = [str(ex[i]) if i < len(ex) else default[i] for i in range(len(recs))]
            return str(data.get("summary", "")), merged
        except Exception as e:
            self.last_error = str(e)
            return "", default
