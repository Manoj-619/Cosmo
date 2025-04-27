# NOTE: Will define constants here, such as prefixes for task names or for cache keys
# This will help in invalidating cache keys or in identifying tasks

# Cache suffixes

HISTORY_SUFFIX         = "history"
USER_PROFILE_SUFFIX    = "data"
CONTEXT_SUFFIX         = "context"
DEFAULT_CACHE_TIMEOUT = 24*60*60*7 # 7 days

# Stage order mapping - should match FourDSequence.Stage enum values in models.py
# The numeric values represent the stage's position in the sequence
# 'profile' is a special stage that occurs before the 4D sequence starts
STAGE_ORDER = {
    "profile": 0,      # Special stage before sequence starts
    "discover": 1,      # FourDSequence.Stage.DISCOVER
    "discuss": 2,       # FourDSequence.Stage.DISCUSS
    "deliver": 3,       # FourDSequence.Stage.DELIVER
    "demonstrate": 4,   # FourDSequence.Stage.DEMONSTRATE
    "completed": 5,     # FourDSequence.Stage.COMPLETED
    "tna_assessment": 1.5  # Special stage between discover and discuss
}