import random
import time

from django.conf import settings
from django.core.cache import cache


def _ttl(base: int) -> int:
    jitter = settings.CACHE_TTL_JITTER_PERCENT / 100.0
    delta = int(base * jitter)
    return max(1, base + random.randint(-delta, delta))


class AuthCacheService:
    """Authz-versioned cache with stampede protection (MD §33–36)."""

    def user_key(self, clerk_user_id: str) -> str:
        return f"auth:user:{clerk_user_id}"

    def context_key(self, user_id: str, org_id: str, loc_id: str, authz_version: int) -> str:
        return f"auth:ctx:v{authz_version}:{user_id}:{org_id}:{loc_id}"

    def get_user(self, clerk_user_id: str):
        try:
            return cache.get(self.user_key(clerk_user_id))
        except Exception:  # noqa: BLE001 — Redis down → DB path
            return None

    def set_user(self, clerk_user_id: str, payload: dict):
        try:
            cache.set(
                self.user_key(clerk_user_id),
                payload,
                timeout=_ttl(settings.AUTH_USER_CACHE_TTL_SECONDS),
            )
        except Exception:  # noqa: BLE001
            pass

    def invalidate_user(self, clerk_user_id: str):
        try:
            cache.delete(self.user_key(clerk_user_id))
        except Exception:  # noqa: BLE001
            pass

    def get_context(self, user_id: str, org_id: str, loc_id: str, authz_version: int):
        try:
            return cache.get(self.context_key(user_id, org_id, loc_id, authz_version))
        except Exception:  # noqa: BLE001
            return None

    def set_context(self, user_id: str, org_id: str, loc_id: str, authz_version: int, payload: dict):
        try:
            cache.set(
                self.context_key(user_id, org_id, loc_id, authz_version),
                payload,
                timeout=_ttl(settings.AUTH_CONTEXT_CACHE_TTL_SECONDS),
            )
        except Exception:  # noqa: BLE001
            pass

    def set_negative(self, key: str):
        try:
            cache.set(f"neg:{key}", True, timeout=_ttl(settings.AUTH_NEGATIVE_CACHE_TTL_SECONDS))
        except Exception:  # noqa: BLE001
            pass

    def has_negative(self, key: str) -> bool:
        try:
            return bool(cache.get(f"neg:{key}"))
        except Exception:  # noqa: BLE001
            return False

    def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        """SET NX style lock for stampede protection."""
        try:
            return cache.add(f"lock:{key}", str(time.time()), timeout=ttl)
        except Exception:  # noqa: BLE001
            return True  # degrade: allow through

    def release_lock(self, key: str):
        try:
            cache.delete(f"lock:{key}")
        except Exception:  # noqa: BLE001
            pass

    def with_stampede(self, key: str, filler, *, ttl_lock: int = 30):
        """Single-flight fill: acquire lock → filler() → release."""
        if not self.acquire_lock(key, ttl=ttl_lock):
            # Wait briefly for winner
            for _ in range(10):
                time.sleep(0.05)
                # caller should re-check cache
            return None
        try:
            return filler()
        finally:
            self.release_lock(key)
