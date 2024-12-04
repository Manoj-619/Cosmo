# NOTE: Will define constants here, such as prefixes for task names or for cache keys
# This will help in invalidating cache keys or in identifying tasks

# Cache suffixes

HISTORY_SUFFIX         = "history"
USER_PROFILE_SUFFIX    = "data"
CONTEXT_SUFFIX         = "context"
DEFAULT_CACHE_TIMEOUT = 24*60*60*7 # 7 days

STAGE_ORDER = {
    "profile": 1,
    "tna_assessment": 2,
    "discover": 3,
    "discuss": 4,
    "deliver": 5,
    "demonstrate": 6
}