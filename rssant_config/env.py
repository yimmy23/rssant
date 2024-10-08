import hashlib
import os.path
import re
from functools import cached_property
from urllib.parse import urlparse

from dotenv import load_dotenv
from validr import Compiler, Invalid, T, fields, modelclass

MAX_FEED_COUNT = 5000

compiler = Compiler()


@modelclass(compiler=compiler)
class ConfigModel:
    pass


class GitHubConfigModel(ConfigModel):
    domain: str = T.str
    client_id: str = T.str
    secret: str = T.str


class EnvConfig(ConfigModel):
    debug: bool = T.bool.default(False).desc('debug')
    profiler_enable: bool = T.bool.default(False).desc('enable profiler or not')
    debug_toolbar_enable: bool = T.bool.default(False).desc(
        'enable debug toolbar or not'
    )
    log_level: str = T.enum('DEBUG,INFO,WARNING,ERROR').default('INFO')
    root_url: str = T.url.default('http://localhost:6789')
    harbor_url: str = T.url.default('http://localhost:6788')
    worker_url: str = T.url.default('http://localhost:6793')
    scheduler_num_worker: int = T.int.min(1).default(10)
    role: str = T.enum('api,worker,scheduler,asyncapi').default('api')
    standby_domains: str = T.str.optional
    secret_key: str = T.str.default(
        '8k1v_4#kv4+3qu1=ulp+@@#65&++!fl1(e*7)ew&nv!)cq%e2y'
    )
    service_secret: str = T.str.optional.desc('service secret')
    image_token_secret: str = T.str.optional.desc('image proxy token secret')
    allow_private_address: bool = T.bool.default(False)
    check_feed_minutes: int = T.int.min(1).default(30)
    feed_story_retention: int = (
        T.int.min(1).default(5000).desc('max storys to keep per feed')
    )
    pg_story_volumes: str = T.str.optional
    feed_reader_request_timeout: int = T.int.default(30).desc(
        'feed reader request timeout'
    )
    # postgres database
    pg_host: str = T.str.default('localhost').desc('postgres host')
    pg_port: int = T.int.default(5432).desc('postgres port')
    pg_db: str = T.str.default('rssant').desc('postgres database')
    pg_user: str = T.str.default('rssant').desc('postgres user')
    pg_password: str = T.str.default('rssant').desc('postgres password')
    # github login
    github_client_id: str = T.str.optional
    github_secret: str = T.str.optional
    github_standby_configs: str = T.str.optional.desc('domain,client_id,secret;')
    # email smtp
    admin_email: str = T.email.default('admin@localhost.com')
    smtp_enable: bool = T.bool.default(False)
    smtp_host: str = T.str.optional
    smtp_port: int = T.int.min(0).optional
    smtp_username: str = T.str.optional
    smtp_password: str = T.str.optional
    smtp_use_ssl: bool = T.bool.default(False)
    # rss proxy
    rss_proxy_url: str = T.url.optional
    rss_proxy_token: str = T.str.optional
    rss_proxy_enable: bool = T.bool.default(False)
    # http proxy or socks proxy
    proxy_url: str = T.url.scheme('http https socks5').optional
    proxy_enable: bool = T.bool.default(False)
    # ezproxy
    ezproxy_base_url: str = T.url.optional
    ezproxy_apikey: str = T.str.default('ezproxy')
    ezproxy_chain_cn: str = T.str.default('cn')
    ezproxy_chain_global: str = T.str.default('default')
    ezproxy_enable: bool = T.bool.default(False)
    # analytics baidu
    analytics_baidu_tongji_enable: bool = T.bool.default(False)
    analytics_baidu_tongji_id: str = T.str.optional
    # analytics clarity
    analytics_clarity_enable: bool = T.bool.default(False)
    analytics_clarity_code: str = T.str.optional
    # analytics google
    analytics_google_enable: bool = T.bool.default(False)
    analytics_google_tracking_id: str = T.str.optional
    # analytics plausible
    analytics_plausible_enable: str = T.bool.default(False)
    analytics_plausible_url: str = T.str.optional
    analytics_plausible_domain: str = T.str.optional
    # ezrevenue
    ezrevenue_enable: bool = T.bool.default(False)
    ezrevenue_project_id: str = T.str.optional
    ezrevenue_project_secret: str = T.str.optional
    ezrevenue_base_url: str = T.url.optional
    # image proxy
    image_proxy_enable: bool = T.bool.default(True)
    image_proxy_urls: bool = T.str.default('origin').desc('逗号分隔的URL列表')
    image_token_expires: float = T.timedelta.min('1s').default('30m')
    detect_story_image_enable: bool = T.bool.default(False)
    # hashid salt
    hashid_salt: str = T.str.default('rssant')

    @property
    def is_role_api(self):
        return self.role == 'api'

    @classmethod
    def _parse_story_volumes(cls, text: str):
        """
        Format:
            {volume}:{user}:{password}@{host}:{port}/{db}/{table}
            {volume}:{table}
        >>> volumes = EnvConfig._parse_story_volumes('0:user:password@host:5432/db/table')
        >>> expect = {0: dict(
        ...    user='user', password='password',
        ...    host='host', port=5432, db='db', table='table'
        ... )}
        >>> volumes == expect
        True
        """
        re_volume = re.compile(
            r'^(\d+)\:([^:@/]+)\:([^:@/]+)\@([^:@/]+)\:(\d+)\/([^:@/]+)\/([^:@/]+)$'
        )
        re_simple_volume = re.compile(r'^(\d+)\:([^:@/]+)$')
        volumes = {}
        for part in text.split(','):
            match = re_volume.match(part)
            is_simple = False
            if not match:
                match = re_simple_volume.match(part)
                is_simple = True
            if not match:
                raise Invalid(f'invalid story volume {part!r}')
            volume = int(match.group(1))
            if is_simple:
                volume_info = dict(table=match.group(2))
            else:
                volume_info = dict(
                    user=match.group(2),
                    password=match.group(3),
                    host=match.group(4),
                    port=int(match.group(5)),
                    db=match.group(6),
                    table=match.group(7),
                )
            volumes[volume] = volume_info
        return volumes

    def _parse_github_standby_configs(self):
        configs = {}
        items = (self.github_standby_configs or '').strip().split(';')
        for item in filter(None, items):
            parts = item.split(',')
            if len(parts) != 3:
                raise Invalid('invalid github standby configs')
            domain, client_id, secret = parts
            configs[domain] = GitHubConfigModel(
                domain=domain, client_id=client_id, secret=secret
            )
        return configs

    def __post_init__(self):
        if not self.service_secret:
            self.service_secret = self._get_extra_secret('service_secret')
        if not self.image_token_secret:
            self.image_token_secret = self._get_extra_secret('image_token_secret')
        if self.smtp_enable:
            if not self.smtp_host:
                raise Invalid('smtp_host is required when smtp_enable=True')
            if not self.smtp_port:
                raise Invalid('smtp_port is required when smtp_enable=True')
        self.pg_story_volumes_parsed = self._get_pg_story_volumes_parsed()
        self.github_standby_configs_parsed = self._parse_github_standby_configs()

    def _get_pg_story_volumes_parsed(self):
        default_story_volume_info = dict(
            user=self.pg_user,
            password=self.pg_password,
            host=self.pg_host,
            port=self.pg_port,
            db=self.pg_db,
            table='story_volume_0',
        )
        if self.pg_story_volumes:
            volumes = {}
            raw_volumes = self._parse_story_volumes(self.pg_story_volumes)
            for volume, volume_info in raw_volumes.items():
                volume_info = dict(default_story_volume_info, **volume_info)
                volumes[volume] = volume_info
        else:
            volumes = {0: default_story_volume_info}
        return volumes

    def _get_extra_secret(self, salt: str):
        payload1 = hashlib.sha256(self.secret_key.encode()).digest()
        payload2 = hashlib.sha256(salt.encode()).digest()
        return hashlib.sha256(payload1 + payload2).hexdigest()[:32]

    @cached_property
    def root_domain(self) -> str:
        return urlparse(self.root_url).hostname

    @cached_property
    def standby_domain_set(self) -> set:
        return set((self.standby_domains or '').strip().split(','))

    @cached_property
    def image_proxy_url_list(self) -> list:
        url_s = (self.image_proxy_urls or '').strip().split(',')
        return list(sorted(set(url_s)))


def load_env_config() -> EnvConfig:
    envfile_path = os.getenv('RSSANT_CONFIG')
    if envfile_path:
        envfile_path = os.path.abspath(os.path.expanduser(envfile_path))
        print(f'* Load envfile at {envfile_path}')
        load_dotenv(envfile_path)
    configs = {}
    for name in fields(EnvConfig):
        key = ('RSSANT_' + name).upper()
        configs[name] = os.environ.get(key, None)
    return EnvConfig(configs)


CONFIG = load_env_config()
