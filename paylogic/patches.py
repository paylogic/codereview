"""Patches to apply to django."""

from django.db.backends.signals import connection_created

from django.db.backends.sqlite3 import base

from django.core.validators import URLValidator


def get_new_connection(sender=None, connection=None, **kwargs):
    """Assign correct text factory when database backend is sqlite3."""
    if sender is base.DatabaseWrapper:
        connection.connection.text_factory = str

# Connect to django signal
connection_created.connect(get_new_connection)

from django.contrib.auth.models import UserManager, User


def get_by_natural_key(self, username):
    return self.get(**{self.model.USERNAME_FIELD: username})

User.USERNAME_FIELD = 'username'

UserManager.get_by_natural_key = get_by_natural_key


old_init = URLValidator.__init__


def validator_init(self, **kwargs):
    if 'message' in kwargs:
        del kwargs['message']
    return old_init(self, **kwargs)


URLValidator.__init__ = validator_init
