import os
import yaml
from django.core.management.base import BaseCommand
from django.conf import settings
from main.models import Tutor

class Command(BaseCommand):
    help = 'Syncs tutors from YAML config files'

    def handle(self, *args, **options):
        # Get the tutors directory path from settings or use a default
        tutors_dir = getattr(settings, 'TUTORS_DIR', os.path.join(settings.BASE_DIR, 'main/tutors'))
        self.stdout.write(
            self.style.SUCCESS(f'{tutors_dir}')
        )
        # Find all .yaml files in the tutors directory
        yaml_files = []
        for root, _, files in os.walk(tutors_dir):
            for file in files:
                if file.endswith('.yaml') or file.endswith('.yml'):
                    yaml_files.append(os.path.join(root, file))
        
        for yaml_path in yaml_files:
            rel_path = os.path.relpath(yaml_path, settings.BASE_DIR)
            try:
                with open(yaml_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Get or create the tutor
                tutor, created = Tutor.objects.update_or_create(
                    config_path=rel_path,
                    defaults={
                        'name': config.get('name'),
                        'deck_name': config.get('deck-name'),
                        'url_path': config.get('url-path'),
                    }
                )
                
                action = 'Created' if created else 'Updated'
                self.stdout.write(
                    self.style.SUCCESS(f'{action} tutor {tutor.name} from {rel_path}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error processing {rel_path}: {str(e)}')
                )
