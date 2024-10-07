import json
import random
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from helpers.utils import md5_sha_from_dict, get_logger
from django.contrib.auth.models import User
from django.conf import settings
from helpers.utils import get_logger
from django.core.cache import cache

# from helpers.constants import () ## NOTE: Will specify some constants soon.

# TODO: 

# 1. API to create a new user. POST request with username/email. To be discussed with Thyagu.

# 2. API to get the user's profile. GET request with username/email.

# 3. API to send/receive messages. POST request with sender, receiver, message. 

