"""Django settings for Universal Accounting Platform auth module."""
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DEBUG=(bool, True),
    CORS_ALLOW_CREDENTIALS=(bool, False),
    CLERK_VERIFY_AUTHORIZED_PARTY=(bool, True),
    IDEMPOTENCY_ENABLED=(bool, True),
    AUTH_SESSION_PROJECTION_ENABLED=(bool, True),
    AUDIT_HASH_IP_ADDRESSES=(bool, True),
    AUDIT_HASH_USER_AGENTS=(bool, True),
    OTEL_ENABLED=(bool, False),
)

environ.Env.read_env(ROOT_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "testserver"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "apps.tenancy",
    "apps.authentication",
    "apps.finance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.authentication.middleware.request_id.RequestIdMiddleware",
    "apps.authentication.middleware.context.TenantContextMiddleware",
    "apps.authentication.middleware.access_log.AccessLogMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://127.0.0.1:6379/1"),
        "KEY_PREFIX": env("REDIS_KEY_PREFIX", default="acct"),
    }
    if env("REDIS_URL", default="")
    else {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "auth-local",
    }
}

AUTH_PASSWORD_VALIDATORS = []  # passwords live in Clerk

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FINANCE_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.authentication.authenticators.clerk.ClerkJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "apps.authentication.exceptions.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.authentication.api.v1.pagination.StandardCursorPagination",
    "PAGE_SIZE": 25,
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Universal Accounting Platform — Auth & Identity API",
    "DESCRIPTION": (
        "Application identity APIs after Clerk authentication. "
        "No /login, /logout, /refresh, or password endpoints — Clerk owns credentials."
    ),
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"ClerkBearer": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "ClerkBearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Clerk session JWT (`Authorization: Bearer <token>`)",
            }
        }
    },
    "TAGS": [
        {"name": "Auth", "description": "Bootstrap, me, context, sessions, security events"},
        {"name": "Finance", "description": "Organization books, journals, periods, reports"},
        {"name": "Webhooks", "description": "Clerk provider webhooks"},
    ],
}

# ---------------------------------------------------------------------------
# CORS / CSRF (STRIDE I2)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_CREDENTIALS = env("CORS_ALLOW_CREDENTIALS")
CORS_ALLOW_HEADERS = list(
    {
        "accept",
        "authorization",
        "content-type",
        "origin",
        "x-request-id",
        "x-organization-id",
        "x-location-id",
        "idempotency-key",
    }
)
CORS_EXPOSE_HEADERS = ["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

# ---------------------------------------------------------------------------
# Clerk
# ---------------------------------------------------------------------------
CLERK_PUBLISHABLE_KEY = env("CLERK_PUBLISHABLE_KEY", default="")
CLERK_SECRET_KEY = env("CLERK_SECRET_KEY", default="")
CLERK_JWT_KEY = env("CLERK_JWT_KEY", default="")
CLERK_ISSUER = env("CLERK_ISSUER", default="")
CLERK_JWKS_URL = env(
    "CLERK_JWKS_URL",
    default="",
)
CLERK_WEBHOOK_SIGNING_SECRET = env("CLERK_WEBHOOK_SIGNING_SECRET", default="")
CLERK_AUTHORIZED_PARTIES = env.list("CLERK_AUTHORIZED_PARTIES", default=[])
CLERK_VERIFY_AUTHORIZED_PARTY = env("CLERK_VERIFY_AUTHORIZED_PARTY")
CLERK_CLOCK_SKEW_MS = env.int("CLERK_CLOCK_SKEW_MS", default=5000)

# ---------------------------------------------------------------------------
# Auth module
# ---------------------------------------------------------------------------
PII_HMAC_KEY = env("PII_HMAC_KEY", default="dev-hmac-key-change-me")
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")
AUTH_USER_CACHE_TTL_SECONDS = env.int("AUTH_USER_CACHE_TTL_SECONDS", default=300)
AUTH_CONTEXT_CACHE_TTL_SECONDS = env.int("AUTH_CONTEXT_CACHE_TTL_SECONDS", default=180)
AUTH_NEGATIVE_CACHE_TTL_SECONDS = env.int("AUTH_NEGATIVE_CACHE_TTL_SECONDS", default=20)
CACHE_TTL_JITTER_PERCENT = env.int("CACHE_TTL_JITTER_PERCENT", default=10)
AUTH_SESSION_PROJECTION_ENABLED = env("AUTH_SESSION_PROJECTION_ENABLED")
AUTH_REQUIRE_CONTEXT_FOR_TENANT_APIS = env.bool(
    "AUTH_REQUIRE_CONTEXT_FOR_TENANT_APIS", default=True
)
IDEMPOTENCY_ENABLED = env("IDEMPOTENCY_ENABLED")
IDEMPOTENCY_RECORD_TTL_SECONDS = env.int("IDEMPOTENCY_RECORD_TTL_SECONDS", default=86400)
IDEMPOTENCY_LOCK_TTL_SECONDS = env.int("IDEMPOTENCY_LOCK_TTL_SECONDS", default=60)
AUDIT_HASH_IP_ADDRESSES = env("AUDIT_HASH_IP_ADDRESSES")
AUDIT_HASH_USER_AGENTS = env("AUDIT_HASH_USER_AGENTS")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173")

# ---------------------------------------------------------------------------
# SMTP — application security mail only (Clerk owns auth email)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="security@example.com")
SECURITY_NOTIFY_EMAIL_ENABLED = env.bool("SECURITY_NOTIFY_EMAIL_ENABLED", default=True)

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=env("REDIS_URL", default="redis://127.0.0.1:6379/0"))
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "apps.authentication.tasks.webhook_tasks.*": {"queue": "webhooks"},
    "apps.authentication.tasks.security_tasks.*": {"queue": "security"},
    "apps.authentication.tasks.maintenance_tasks.*": {"queue": "maintenance"},
}

AUTH_BOOTSTRAP_RATE_LIMIT = env("AUTH_BOOTSTRAP_RATE_LIMIT", default="30/m")
AUTH_ME_RATE_LIMIT = env("AUTH_ME_RATE_LIMIT", default="180/m")
AUTH_CONTEXT_RATE_LIMIT = env("AUTH_CONTEXT_RATE_LIMIT", default="120/m")
AUTH_CONTEXT_SWITCH_RATE_LIMIT = env("AUTH_CONTEXT_SWITCH_RATE_LIMIT", default="30/m")
AUTH_SECURITY_EVENTS_RATE_LIMIT = env("AUTH_SECURITY_EVENTS_RATE_LIMIT", default="30/m")
AUTH_SESSIONS_RATE_LIMIT = env("AUTH_SESSIONS_RATE_LIMIT", default="60/m")
PROVIDER_EVENT_RETENTION_DAYS = env.int("PROVIDER_EVENT_RETENTION_DAYS", default=30)
SECURITY_EVENT_RETENTION_DAYS = env.int("SECURITY_EVENT_RETENTION_DAYS", default=90)
DB_CONN_MAX_AGE = env.int("DB_CONN_MAX_AGE", default=60)
DB_CONNECT_TIMEOUT_SECONDS = env.int("DB_CONNECT_TIMEOUT_SECONDS", default=5)
DB_STATEMENT_TIMEOUT_MS = env.int("DB_STATEMENT_TIMEOUT_MS", default=15000)

# Optional: apply statement timeout on Postgres
if DATABASES["default"].get("ENGINE", "").endswith("postgresql"):
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["CONN_MAX_AGE"] = DB_CONN_MAX_AGE
    DATABASES["default"]["OPTIONS"].setdefault(
        "options", f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}"
    )

# ---------------------------------------------------------------------------
# Celery beat (reconciliation / cleanup)
# ---------------------------------------------------------------------------
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "reconcile-unprocessed-webhooks": {
        "task": "apps.authentication.tasks.maintenance_tasks.reconcile_unprocessed_webhooks",
        "schedule": 120.0,
    },
    "cleanup-idempotency": {
        "task": "apps.authentication.tasks.maintenance_tasks.cleanup_expired_idempotency",
        "schedule": crontab(minute=0, hour=3),
    },
    "cleanup-provider-events": {
        "task": "apps.authentication.tasks.maintenance_tasks.cleanup_provider_events",
        "schedule": crontab(minute=30, hour=3),
    },
    "expire-session-projections": {
        "task": "apps.authentication.tasks.maintenance_tasks.expire_local_session_projection",
        "schedule": crontab(minute=0, hour=4),
    },
    "finance-recurring-run": {
        "task": "apps.finance.tasks.run_due_recurring",
        "schedule": crontab(minute=15, hour=1),
    },
    "finance-reminder-run": {
        "task": "apps.finance.tasks.run_due_reminders",
        "schedule": crontab(minute=30, hour=1),
    },
    "finance-feed-run": {
        "task": "apps.finance.tasks.run_due_feeds",
        "schedule": crontab(minute=45, hour=2),
    },
}

# ---------------------------------------------------------------------------
# Sentry / OpenTelemetry (optional)
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="development")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0)
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=SENTRY_ENVIRONMENT,
            traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
            integrations=[DjangoIntegration()],
            send_default_pii=False,
        )
    except ImportError:
        pass

OTEL_ENABLED = env("OTEL_ENABLED")
OTEL_SERVICE_NAME = env("OTEL_SERVICE_NAME", default="universal-accounting-api")
OTEL_EXPORTER_OTLP_ENDPOINT = env("OTEL_EXPORTER_OTLP_ENDPOINT", default="")
if OTEL_ENABLED and OTEL_EXPORTER_OTLP_ENDPOINT:
    try:
        from opentelemetry.instrumentation.django import DjangoInstrumentor

        DjangoInstrumentor().instrument()
    except ImportError:
        pass

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.authentication.logging_utils.JsonFormatter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
