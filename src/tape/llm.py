"""LLM backends for candidate-plan generation.

Two implementations sharing one interface (`generate_candidate_plans`):
  - MockLLMClient: goal-biased random search. No network/API key needed --
    used for tests and offline development.
  - GeminiClient: calls the Gemini REST API directly over `urllib` (no SDK,
    to avoid the multi-hundred-MB google-generativeai/grpc dependency chain
    for what is a single POST request).
"""
from __future__ import annotations

import json
import os
import random
import re
import urllib.request
from collections import deque
from typing import Protocol

from tape.envs.sokoban import ACTIONS, SokobanLevel, State

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


class LLMClient(Protocol):
    def generate_candidate_plans(
        self, level: SokobanLevel, state: State, n: int, max_depth: int
    ) -> list[list[str]]: ...


def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _bfs_plan(level: SokobanLevel, start: State, max_depth: int) -> list[str]:
    """Shortest solving action sequence within max_depth, or [] if none.
    Used as one "good" candidate among the mock LLM's proposals -- a real
    LLM occasionally gets it exactly right too."""
    frontier = deque([(start, [])])
    seen = {start}
    while frontier:
        cur, path = frontier.popleft()
        if level.is_goal(cur):
            return path
        if len(path) >= max_depth:
            continue
        for a in ACTIONS:
            nxt, moved = level.step(cur, a)
            if moved and nxt not in seen:
                seen.add(nxt)
                frontier.append((nxt, path + [a]))
    return []


class MockLLMClient:
    """Stands in for an LLM: proposes one BFS-optimal candidate plus `n-1`
    noisy goal-biased-random-walk candidates, so the graph-merging and
    solver stages have a realistic mix (one good plan buried in imperfect,
    sometimes dead-ending ones) to work with -- without depending on an API
    key for tests and offline development.
    """

    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)

    def generate_candidate_plans(
        self, level: SokobanLevel, state: State, n: int, max_depth: int
    ) -> list[list[str]]:
        plans = [_bfs_plan(level, state, max_depth)]
        for _ in range(max(0, n - 1)):
            plans.append(self._noisy_candidate(level, state, max_depth))
        return plans

    def _noisy_candidate(self, level: SokobanLevel, state: State, max_depth: int) -> list[str]:
        actions: list[str] = []
        cur = state
        for _ in range(max_depth):
            if level.is_goal(cur):
                break
            scored = []
            for a in ACTIONS:
                nxt, moved = level.step(cur, a)
                if not moved:
                    continue
                dist = sum(
                    min(_manhattan(b, g) for g in level.goals) for b in nxt.boxes
                )
                scored.append((dist, a, nxt))
            if not scored:
                break
            scored.sort(key=lambda t: t[0])
            top_k = scored[: max(1, len(scored) // 2 + 1)]
            _, action, cur = self._rng.choice(top_k)
            actions.append(action)
        return actions


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        self.model = model

    def generate_candidate_plans(
        self, level: SokobanLevel, state: State, n: int, max_depth: int
    ) -> list[list[str]]:
        prompt = self._build_prompt(level, state, n, max_depth)
        text = self._call(prompt)
        return self._parse(text)

    def _build_prompt(self, level: SokobanLevel, state: State, n: int, max_depth: int) -> str:
        return (
            "You are solving a Sokoban puzzle. '#'=wall, '@'=player, '$'=box, "
            "'.'=goal, '*'=box on goal, '+'=player on goal.\n"
            f"{level.render(state)}\n\n"
            f"Propose {n} different candidate action sequences (each a list of "
            "moves from {U,D,L,R}) that could push every box onto a goal, "
            f"each at most {max_depth} moves. Reply with ONLY a JSON array of "
            'arrays, e.g. [["U","R","R"],["D","L"]].'
        )

    def _call(self, prompt: str) -> str:
        url = GEMINI_ENDPOINT.format(model=self.model, key=self.api_key)
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _parse(self, text: str) -> list[list[str]]:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        try:
            raw = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
        return [[a for a in seq if a in ACTIONS] for seq in raw if isinstance(seq, list)]
