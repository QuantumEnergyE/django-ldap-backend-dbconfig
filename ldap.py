from __future__ import absolute_import
from model import AuthProvider, GroupRelationMap
from serializers import AuthProviderSerializer, GroupRelationMapSerializer
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django_auth_ldap.backend import LDAPSettings, LDAPBackend, populate_user
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType
import ldap


class LDAPConfigDB(object):
    config_table = AuthProvider
    config_table_serializer = AuthProviderSerializer

    def __init__(self, cfg_type=None):
        self.cfg_type = cfg_type

    def _get_default_setting(self):
        """
        Get default settings from ldap database
        """
        defaults = {
            'ALWAYS_UPDATE_USER': True,
            'AUTHORIZE_ALL_USERS': False,
            'BIND_AS_AUTHENTICATING_USER': False,
            'BIND_DN': '',
            'BIND_PASSWORD': '',
            'CACHE_GROUPS': False,
            'CONNECTION_OPTIONS': {},
            'DENY_GROUP': None,
            'FIND_GROUP_PERMS': False,
            'GROUP_CACHE_TIMEOUT': None,
            'GROUP_SEARCH': None,
            'GROUP_TYPE': None,
            'MIRROR_GROUPS': None,
            'MIRROR_GROUPS_EXCEPT': None,
            'PERMIT_EMPTY_PASSWORD': False,
            'PROFILE_ATTR_MAP': {},
            'PROFILE_FLAGS_BY_GROUP': {},
            'REQUIRE_GROUP': None,
            'SERVER_URI': 'ldap://localhost',
            'START_TLS': False,
            'USER_ATTRLIST': None,
            'USER_ATTR_MAP': {},
            'USER_DN_TEMPLATE': None,
            'USER_FLAGS_BY_GROUP': {},
            'USER_SEARCH': None,
        }
        db_map = {
            'SERVER_URI': 'provider_url',
            'BIND_DN': 'admin',
            'BIND_PASSWORD': 'password',
            'USER_DN_TEMPLATE': 'user_template',
        }
        db_info = None
        try:
            db_info = self.config_table_serializer(self.config_table.objects.get(type=self.cfg_type)).data
        except Exception as ex:
            print ex
        if not db_info:
            return defaults
        db_defaults = {}
        for k, v in db_map.items():
            if v in db_info.keys():
                db_defaults[k] = db_info[v]
        if not (db_defaults['BIND_DN'] and db_defaults['BIND_PASSWORD']):
            db_defaults['BIND_DN'] = ''
            db_defaults['BIND_PASSWORD'] = ''
            return dict(defaults, **db_defaults)
        db_defaults['USER_DN_TEMPLATE'] = None
        rdn = "(cn=%(user)s)" if db_info['filter_attr'] == "cn" else "(uid=%(user)s)"
        db_defaults['USER_SEARCH'] = LDAPSearch(db_info['search_dn'], ldap.SCOPE_SUBTREE, rdn)
        db_defaults['USER_ATTR_MAP'] = {"first_name": "givenName", "last_name": "sn", "email": "mail"}
        # db_defaults['GROUP_SEARCH'] = LDAPSearch(db_info['search_dn'], ldap.SCOPE_SUBTREE, "(objectClass=group)")
        db_defaults['GROUP_SEARCH'] = LDAPSearch(db_info['search_dn'], ldap.SCOPE_SUBTREE, "(objectClass=*)")
        db_defaults['GROUP_TYPE'] = GroupOfNamesType()
        db_defaults['REQUIRE_GROUP'] = db_info['require_group'] if db_info['require_group'] else None
        db_defaults['USER_FLAGS_BY_GROUP'] = {}
        if db_info['super_group']:
            db_defaults['USER_FLAGS_BY_GROUP']['is_superuser'] = db_info['super_group']
        return dict(defaults, **db_defaults)

    def _get_settings_prefix(self):
        return "AUTH_LDAP_%s_" % self.cfg_type if self.cfg_type else "AUTH_LDAP_"

    default_setting = property(_get_default_setting)
    settings_prefix = property(_get_settings_prefix)


class CustomLDAPSettings(LDAPSettings):
    pass


class CustomLDAPBackend(LDAPBackend):
    """
    the attribute in django's setting file with the settings_prefix can overwrite the config from LDAPConfigDB
    """
    _settings = CustomLDAPSettings()

    def __init__(self, ldap_config=None):
        if not ldap_config:
            return
        settings_prefix = ldap_config.settings_prefix
        default_setting = ldap_config.default_setting
        CustomLDAPBackend._settings = CustomLDAPSettings(settings_prefix, default_setting)

    def authenticate(self, request=None, username=None, password=None, **kwargs):
        """
        if catch exception, allow modelauth
        """
        user = None
        try:
            user = super(CustomLDAPBackend, self).authenticate(request, username, password, **kwargs)
        except Exception as ex:
            print ex
        return user


class OpenLDAPBackend(CustomLDAPBackend):
    def __init__(self):
        ldap_config = LDAPConfigDB(cfg_type='ldap')
        super(OpenLDAPBackend, self).__init__(ldap_config)


class WinADBackend(CustomLDAPBackend):
    def __init__(self):
        ldap_config = LDAPConfigDB(cfg_type='ad')
        super(WinADBackend, self).__init__(ldap_config)


@receiver(populate_user)
def update_groups(sender, user=None, ldap_user=None, **kwargs):
    """
    map django groups to django groups
    :param sender:
    :param user: User
    :param ldap_user: _LDAPUser
    :param kwargs:
    :return:
    """
    user.groups.clear()  # clear user's all groups
    group_map = {}
    data = GroupRelationMapSerializer(GroupRelationMap.objects.all(), many=True).data
    for record in data:
        group_map[record['ldap_group']] = record['dj_group']
    group_names = ldap_user.group_names
    for ldap_group in group_names:
        dj_group = group_map.get(ldap_group, None)
        if dj_group:
            group = Group.objects.get_or_create(name=dj_group)
            user.groups.add(group[0])
