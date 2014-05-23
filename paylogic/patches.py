"""Patches to apply to django."""

from django.db.backends.signals import connection_created

from django.db.backends.sqlite3 import base


def get_new_connection(sender=None, connection=None, **kwargs):
    """Assign correct text factory when database backend is sqlite3"""
    if sender is base.DatabaseWrapper:
        connection.connection.text_factory = str

# Connect to django signal
connection_created.connect(get_new_connection)
