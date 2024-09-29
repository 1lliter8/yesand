from django.core.management.base import BaseCommand

from yesand.models import Dir


class Command(BaseCommand):
    help = 'Adds a default Dir with display="Project 1" if no Dir exists'

    def handle(self, *args, **options):
        if not Dir.objects.exists():
            Dir.objects.create(display='Project 1')
            self.stdout.write(
                self.style.SUCCESS('Successfully created default project')
            )
        else:
            self.stdout.write(
                self.style.WARNING('A project already exists. No action taken.')
            )
