from __future__ import annotations

import os
import time
import functools
from datetime import datetime, timezone
from typing import Any, Callable

import tweepy
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()

# Daily read budget — max X API read calls per day (writes always go through)
DAILY_READ_BUDGET = int(os.getenv("DAILY_API_BUDGET", "60"))


def _get_read_count() -> int:
    """Get today's API read call count from agent_state table."""
    try:
        from tools.memory import get_agent_state
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        val = get_agent_state(f"api_reads_{today}")
        return int(val) if val else 0
    except Exception:
        return 0


def _increment_read_count() -> int:
    """Increment today's read count. Returns new count."""
    try:
        from tools.memory import get_agent_state, set_agent_state
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = f"api_reads_{today}"
        count = int(get_agent_state(key) or 0) + 1
        set_agent_state(key, str(count))
        return count
    except Exception:
        return 0


def _within_budget() -> bool:
    """Return True if we're still within today's read budget."""
    count = _get_read_count()
    if count >= DAILY_READ_BUDGET:
        console.print(
            f"[yellow]Daily API read budget ({DAILY_READ_BUDGET}) reached "
            f"({count} calls today). Skipping read call.[/yellow]"
        )
        return False
    return True


def _exponential_backoff(max_retries: int = 5, base_delay: float = 1.0) -> Callable:
    """Decorator that retries on rate-limit errors with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except tweepy.errors.TooManyRequests as e:
                    if attempt == max_retries - 1:
                        console.print(
                            f"[red]Rate limit hit on {func.__name__} after {max_retries} retries. Giving up.[/red]"
                        )
                        return None
                    delay = base_delay * (2 ** attempt)
                    console.print(
                        f"[yellow]Rate limit hit on {func.__name__}. "
                        f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...[/yellow]"
                    )
                    time.sleep(delay)
                except tweepy.errors.TwitterServerError as e:
                    if attempt == max_retries - 1:
                        console.print(f"[red]Twitter server error on {func.__name__}: {e}[/red]")
                        return None
                    delay = base_delay * (2 ** attempt)
                    console.print(f"[yellow]Twitter server error, retrying in {delay:.1f}s...[/yellow]")
                    time.sleep(delay)
                except Exception as e:
                    console.print(f"[red]Error in {func.__name__}: {e}[/red]")
                    return None
            return None
        return wrapper
    return decorator


class XAPIClient:
    """Tweepy v2 wrapper with dry-run support and exponential backoff."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._client: tweepy.Client | None = None
        self._api_v1: tweepy.API | None = None
        self._me_id: str | None = None  # cached user ID
        self._user_id_cache: dict[str, str] = self._load_user_id_cache()
        self._initialize_clients()

    def _load_user_id_cache(self) -> dict[str, str]:
        """Load persisted username→user_id cache from DB to avoid lookups on restart."""
        try:
            from tools.memory import get_agent_state
            val = get_agent_state("user_id_cache")
            if val:
                import json
                return json.loads(val)
        except Exception:
            pass
        return {}

    def _save_user_id_cache(self) -> None:
        """Persist the username→user_id cache to DB."""
        try:
            from tools.memory import set_agent_state
            import json
            set_agent_state("user_id_cache", json.dumps(self._user_id_cache))
        except Exception:
            pass

    def _initialize_clients(self) -> None:
        """Initialize Tweepy v2 Client and v1.1 API."""
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        bearer_token = os.getenv("X_BEARER_TOKEN")

        if not all([api_key, api_secret, access_token, access_token_secret, bearer_token]):
            console.print(
                "[yellow]Warning: Some X API credentials missing. "
                "Set them in .env to enable API functionality.[/yellow]"
            )
            return

        try:
            self._client = tweepy.Client(
                bearer_token=bearer_token,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=False,
            )

            auth = tweepy.OAuth1UserHandler(
                api_key, api_secret, access_token, access_token_secret
            )
            self._api_v1 = tweepy.API(auth, wait_on_rate_limit=False)
            console.print("[green]X API clients initialized.[/green]")
        except Exception as e:
            console.print(f"[red]Failed to initialize X API: {e}[/red]")

    def _require_client(self) -> bool:
        """Return True if client is available."""
        if self._client is None:
            console.print("[red]X API client not initialized. Check .env credentials.[/red]")
            return False
        return True

    @_exponential_backoff(max_retries=5)
    def post_tweet(self, text: str, reply_to_id: str | None = None) -> dict[str, Any] | None:
        """Post a single tweet. Returns response dict or None."""
        if self.dry_run:
            console.print(
                f"[cyan][DRY RUN] Would post tweet ({len(text)} chars):\n{text}[/cyan]"
            )
            return {"id": "dry_run_id", "text": text}

        if not self._require_client():
            return None

        kwargs: dict[str, Any] = {"text": text}
        if reply_to_id:
            kwargs["in_reply_to_tweet_id"] = reply_to_id

        response = self._client.create_tweet(**kwargs)  # type: ignore[union-attr]
        if response and response.data:
            tweet_id = response.data["id"]
            console.print(f"[green]Tweet posted: {tweet_id}[/green]")
            return {"id": tweet_id, "text": text}
        return None

    def post_thread(self, tweets: list[str]) -> list[dict[str, Any]]:
        """Post a thread. Returns list of response dicts."""
        if self.dry_run:
            console.print(f"[cyan][DRY RUN] Would post thread ({len(tweets)} tweets):[/cyan]")
            for i, t in enumerate(tweets, 1):
                console.print(f"[cyan]  [{i}/{len(tweets)}] {t[:100]}...[/cyan]" if len(t) > 100 else f"[cyan]  [{i}/{len(tweets)}] {t}[/cyan]")
            return [{"id": f"dry_run_id_{i}", "text": t} for i, t in enumerate(tweets)]

        results: list[dict[str, Any]] = []
        reply_to: str | None = None
        for tweet_text in tweets:
            result = self.post_tweet(tweet_text, reply_to_id=reply_to)
            if result:
                results.append(result)
                reply_to = result.get("id")
                time.sleep(1.5)  # Small delay between thread tweets
            else:
                console.print("[red]Thread interrupted — tweet failed. Stopping.[/red]")
                break
        return results

    @_exponential_backoff(max_retries=3)
    def search_recent_tweets(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search recent tweets. Returns list of tweet dicts."""
        if not self._require_client():
            return []
        if not _within_budget():
            return []
        _increment_read_count()

        # Cap at API limits
        max_results = min(max(10, max_results), 100)

        response = self._client.search_recent_tweets(  # type: ignore[union-attr]
            query=query,
            max_results=max_results,
            tweet_fields=["created_at", "public_metrics", "author_id", "text"],
            expansions=["author_id"],
            user_fields=["public_metrics", "username"],
        )

        if not response or not response.data:
            return []

        users_by_id: dict[str, Any] = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                users_by_id[str(user.id)] = user

        results: list[dict[str, Any]] = []
        for tweet in response.data:
            author = users_by_id.get(str(tweet.author_id), None)
            metrics = tweet.public_metrics or {}
            results.append(
                {
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": str(tweet.created_at) if tweet.created_at else None,
                    "author_id": str(tweet.author_id),
                    "username": author.username if author else None,
                    "follower_count": (
                        author.public_metrics.get("followers_count", 0)
                        if author and author.public_metrics
                        else 0
                    ),
                    "like_count": metrics.get("like_count", 0),
                    "retweet_count": metrics.get("retweet_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                    "impression_count": metrics.get("impression_count", 0),
                }
            )
        return results

    @_exponential_backoff(max_retries=3)
    def get_mentions(self, since_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch recent mentions. Returns list of mention dicts."""
        if not self._require_client():
            return []
        if not _within_budget():
            return []
        _increment_read_count()

        kwargs: dict[str, Any] = {
            "tweet_fields": ["created_at", "public_metrics", "author_id", "text"],
            "expansions": ["author_id"],
            "user_fields": ["public_metrics", "username"],
            "max_results": 20,
        }
        if since_id:
            kwargs["since_id"] = since_id

        # Get authenticated user's ID (cached after first call)
        if not self._me_id:
            me = self._client.get_me()  # type: ignore[union-attr]
            if not me or not me.data:
                console.print("[red]Could not get authenticated user info.[/red]")
                return []
            self._me_id = str(me.data.id)

        response = self._client.get_users_mentions(  # type: ignore[union-attr]
            id=self._me_id, **kwargs
        )

        if not response or not response.data:
            return []

        users_by_id: dict[str, Any] = {}
        if response.includes and "users" in response.includes:
            for user in response.includes["users"]:
                users_by_id[str(user.id)] = user

        results: list[dict[str, Any]] = []
        for tweet in response.data:
            author = users_by_id.get(str(tweet.author_id), None)
            metrics = tweet.public_metrics or {}
            results.append(
                {
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": str(tweet.created_at) if tweet.created_at else None,
                    "author_id": str(tweet.author_id),
                    "username": author.username if author else "unknown",
                    "follower_count": (
                        author.public_metrics.get("followers_count", 0)
                        if author and author.public_metrics
                        else 0
                    ),
                    "like_count": metrics.get("like_count", 0),
                }
            )
        return results

    @_exponential_backoff(max_retries=3)
    def get_tweet_metrics(self, tweet_id: str) -> dict[str, Any] | None:
        """Get public metrics for a tweet."""
        if not self._require_client():
            return None
        if not _within_budget():
            return None
        _increment_read_count()

        response = self._client.get_tweet(  # type: ignore[union-attr]
            id=tweet_id,
            tweet_fields=["public_metrics", "non_public_metrics", "organic_metrics"],
        )

        if not response or not response.data:
            return None

        metrics: dict[str, Any] = {}
        if response.data.public_metrics:
            metrics.update(response.data.public_metrics)
        if hasattr(response.data, "non_public_metrics") and response.data.non_public_metrics:
            metrics.update(response.data.non_public_metrics)
        if hasattr(response.data, "organic_metrics") and response.data.organic_metrics:
            metrics.update(response.data.organic_metrics)

        return {
            "impressions": metrics.get("impression_count", 0),
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "bookmarks": metrics.get("bookmark_count", 0),
        }

    @_exponential_backoff(max_retries=3)
    def get_user_timeline(
        self,
        username: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Fetch recent tweets from a user's timeline."""
        if not self._require_client():
            return []

        if not _within_budget():
            return []

        # Look up user ID (cached to avoid repeated API calls)
        follower_count = 0
        if username in self._user_id_cache:
            user_id = self._user_id_cache[username]
        else:
            _increment_read_count()
            user_resp = self._client.get_user(  # type: ignore[union-attr]
                username=username,
                user_fields=["public_metrics"],
            )
            if not user_resp or not user_resp.data:
                console.print(f"[yellow]User not found: {username}[/yellow]")
                return []
            user_id = user_resp.data.id
            self._user_id_cache[username] = str(user_id)
            self._save_user_id_cache()  # persist so restart doesn't re-fetch
            if user_resp.data.public_metrics:
                follower_count = user_resp.data.public_metrics.get("followers_count", 0)

        max_results = min(max(5, max_results), 100)
        response = self._client.get_users_tweets(  # type: ignore[union-attr]
            id=user_id,
            max_results=max_results,
            tweet_fields=["created_at", "public_metrics", "text"],
            exclude=["retweets", "replies"],
        )

        if not response or not response.data:
            return []

        results: list[dict[str, Any]] = []
        for tweet in response.data:
            metrics = tweet.public_metrics or {}
            results.append(
                {
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": str(tweet.created_at) if tweet.created_at else None,
                    "username": username,
                    "follower_count": follower_count,
                    "like_count": metrics.get("like_count", 0),
                    "retweet_count": metrics.get("retweet_count", 0),
                    "reply_count": metrics.get("reply_count", 0),
                }
            )
        return results

    @_exponential_backoff(max_retries=3)
    def get_user_info(self, username: str) -> dict[str, Any] | None:
        """Get user profile info."""
        if not self._require_client():
            return None

        response = self._client.get_user(  # type: ignore[union-attr]
            username=username,
            user_fields=["public_metrics", "created_at", "description", "verified"],
        )

        if not response or not response.data:
            return None

        user = response.data
        metrics = user.public_metrics or {}
        return {
            "id": str(user.id),
            "username": user.username,
            "name": user.name,
            "description": getattr(user, "description", ""),
            "follower_count": metrics.get("followers_count", 0),
            "following_count": metrics.get("following_count", 0),
            "tweet_count": metrics.get("tweet_count", 0),
            "verified": getattr(user, "verified", False),
            "created_at": str(user.created_at) if hasattr(user, "created_at") and user.created_at else None,
        }
