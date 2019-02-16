from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField


class RssFeed(models.Model):
    """供稿"""

    class Meta:
        indexes = [
            models.Index(fields=["user", "dt_updated"]),
            models.Index(fields=["url"]),
        ]

    STSTUSES = [
        ('pending', "pending"),
        ('updating', "updating"),
        ('ready', "ready"),
        ('error', "error"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STSTUSES, default='pending', help_text='状态')
    url = models.URLField(help_text="供稿地址")
    # 从 feed 中提取的字段
    title = models.CharField(max_length=200, blank=True, help_text="标题")
    link = models.URLField(blank=True, help_text="网站链接")
    author = models.CharField(max_length=200, blank=True, help_text="作者")
    icon = models.URLField(blank=True, help_text="网站Logo或图标")
    description = models.TextField(blank=True, help_text="描述或小标题")
    version = models.CharField(max_length=200, blank=True, help_text="供稿格式/RSS/Atom")
    dt_created = models.DateTimeField(auto_now_add=True, help_text="创建时间")
    dt_updated = models.DateTimeField(auto_now=True, help_text="更新时间")
    # data from http response
    encoding = models.CharField(max_length=200, blank=True, help_text="编码")
    etag = models.CharField(max_length=200, blank=True, help_text="HTTP response header ETag")
    last_modified = models.CharField(max_length=200, blank=True,
                                     help_text="HTTP response header Last-Modified")
    headers = JSONField(null=True, blank=True, help_text='HTTP response headers, JSON object')
    # data from feedparser
    data = JSONField(null=True, blank=True)

    def asdict(self):
        return dict(
            id=self.id,
            status=self.status,
            url=self.url,
            title=self.title,
            dt_created=self.dt_created,
            dt_updated=self.dt_updated,
        )


class RssStory(models.Model):
    """故事"""

    class Meta:
        indexes = [
            models.Index(fields=["user", "dt_updated"]),
            models.Index(fields=["feed", "dt_updated"]),
            models.Index(fields=["link"]),
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feed = models.ForeignKey(RssFeed, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, blank=True, help_text="标题")
    link = models.URLField(blank=True, help_text="文章链接")
    dt_published = models.DateTimeField(blank=True, help_text="发布时间")
    dt_updated = models.DateTimeField(blank=True, help_text="更新时间")
    summary = models.TextField(blank=True, help_text="摘要或较短的内容")
    content = models.TextField(blank=True, help_text="文章内容")
    # data from feedparser
    data = JSONField(null=True, blank=True)
