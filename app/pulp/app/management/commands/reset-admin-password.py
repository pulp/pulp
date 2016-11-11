from gettext import gettext as _
from getpass import getpass

from django.core.management import BaseCommand, CommandError

from pulp.app.models import User


class Command(BaseCommand):
    """
    Django management command for resetting the password of the 'admin' user in Pulp.
    """
    help = _('Resets "admin" user\'s password.')

    def add_arguments(self, parser):
        parser.add_argument('--random',
                            action='store_true',
                            dest='random',
                            default=False,
                            help=_('Generate random password for \'admin\' user.'))

    def handle(self, *args, **options):
        user = User.objects.get_or_create(username='admin', is_superuser=True)[0]
        if options['random']:
            password = User.objects.make_random_password(length=20)
            user.set_password(password)
            user.save()
            self.stdout.write(_('Successfully set "admin" user\'s password to "%s".') % password)
        else:
            password = getpass(_('Please enter new password for user "admin": '))
            password2 = getpass(_('Please enter new password for user "admin" again: '))
            if not password:
                raise CommandError(_("The password must be at least 1 character long."))
            if password == password2:
                user.set_password(password)
                user.save()
                self.stdout.write(_('Successfully set password for "admin" user.'))
            else:
                raise CommandError(_('The passwords did not match.'))
