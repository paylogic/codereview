from django.core.management.base import BaseCommand
from django.db.models import get_models, get_app
from django.contrib.auth.management import create_permissions


class Command(BaseCommand):
    args = '<app app ...>'
    help = 'reloads permissions for specified apps, or all apps if no args are specified'

    def handle(self, *args, **options):
        if not args:
            apps = [get_app(model._meta.app_label) for model in get_models()]
        else:
            apps = [get_app(arg) for arg in args]
        for app in apps:
            create_permissions(app, get_models(), options.get('verbosity', 0))
