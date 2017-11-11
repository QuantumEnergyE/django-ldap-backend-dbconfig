from django.db import models


class AuthProvider(models.Model):
    """
    Direct Bind:
    if admin or password is empty, will use AUTH_LDAP_USER_DN_TEMPLATE(user_template)
    """
    provider_url = models.CharField(max_length=256, null=True)  # ldap://192.168.10.254:389
    admin = models.CharField(max_length=128, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    search_dn = models.CharField(max_length=1024, null=True, blank=True)  # cn=example,cn=com

    user_template = models.CharField(max_length=256, null=True, blank=True)  # uid=%(user)s,ou=users,dc=example,dc=com
    require_group = models.CharField(max_length=256, null=True, blank=True)  # ou=dj, cn=example, cn=com
    super_group = models.CharField(max_length=256, null=True, blank=True)  # ou=dj_admin, cn=example, cn=com
    filter_attr = models.CharField(max_length=32, default='cn')  # cn or uid
    type = models.CharField(max_length=32)  # ldap or ad or ...


class GroupRelationMap(models.Model):
    """
    map group relation
    """
    ldap_group = models.CharField(max_length=128)  # ldap group's name
    dj_group = models.CharField(max_length=128)  # django group's name
