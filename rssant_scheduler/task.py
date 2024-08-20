import datetime
import logging

from rssant_common.validator import T, compiler

LOG = logging.getLogger(__name__)

_validate_timer = compiler.compile(T.timedelta.object)


def Timer(value) -> datetime.timedelta:
    return _validate_timer(value)


SCHEDULER_TASK_S = [
    dict(
        api='harbor_rss.clean_feed_creation',
        timer=Timer('1m'),
    ),
    dict(
        api='harbor_rss.clean_by_retention',
        timer=Timer('1m'),
    ),
    dict(
        api='harbor_rss.clean_feedurlmap_by_retention',
        timer=Timer('30m'),
    ),
    dict(
        api='harbor_rss.feed_refresh_freeze_level',
        timer=Timer('40m'),
    ),
    dict(
        api='harbor_rss.feed_detect_and_merge_duplicate',
        timer=Timer('4h'),
    ),
    dict(
        api='harbor_django.clear_expired_sessions',
        timer=Timer('6h'),
    ),
]
