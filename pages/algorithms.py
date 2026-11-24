"""Struktur data dan algoritma yang dipakai TuneMatch."""
import math
from collections import deque


class Stack:
    """Stack (LIFO): dipakai untuk fitur Undo penghapusan lagu dari playlist."""

    def __init__(self):
        self._items = []

    def push(self, item):
        self._items.append(item)

    def pop(self):
        return self._items.pop() if self._items else None

    def __len__(self):
        return len(self._items)


class Queue:
    """Queue (FIFO) berbasis deque: dipakai untuk antrean putar lagu."""

    def __init__(self):
        self._items = deque()

    def enqueue(self, item):
        self._items.append(item)

    def dequeue(self):
        return self._items.popleft() if self._items else None

    def items(self):
        return list(self._items)

    def __len__(self):
        return len(self._items)


def merge_sort(items, key=lambda x: x, reverse=False):
    """Merge sort stabil O(n log n) pada list; mengembalikan list baru."""
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    left = merge_sort(items[:mid], key, reverse)
    right = merge_sort(items[mid:], key, reverse)
    out, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        a, b = key(left[i]), key(right[j])
        take_left = a >= b if reverse else a <= b
        if take_left:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out


def binary_search_prefix(sorted_items, prefix, key=lambda x: x):
    """Binary search pada list yang sudah terurut menurut `key`.
    Mengembalikan semua item yang kuncinya diawali `prefix`."""
    lo, hi = 0, len(sorted_items)
    while lo < hi:  # lower bound
        mid = (lo + hi) // 2
        if key(sorted_items[mid]) < prefix:
            lo = mid + 1
        else:
            hi = mid
    result = []
    while lo < len(sorted_items) and key(sorted_items[lo]).startswith(prefix):
        result.append(sorted_items[lo])
        lo += 1
    return result


def jaccard(a, b):
    """Kemiripan Jaccard antara dua kumpulan tag (0..1)."""
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def popularity_norm(playcount, max_playcount):
    """Normalisasi popularitas (skala log) ke 0..1."""
    if max_playcount <= 0:
        return 0.0
    return math.log1p(playcount) / math.log1p(max_playcount)


def score_song(match, tag_similarity, popularity):
    """Skor = 0,5 x match Last.fm + 0,3 x Jaccard tag + 0,2 x popularitas."""
    return 0.5 * match + 0.3 * tag_similarity + 0.2 * popularity
