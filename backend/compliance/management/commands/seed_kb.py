"""
Django Management Command: seed_kb
Populates Requirement and SubElement tables from canonical_kb.json or custom specified file.

Usage:
    python manage.py seed_kb
    python manage.py seed_kb --clear
    python manage.py seed_kb --file path/to/file.json
"""

import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from compliance.models import Requirement, SubElement


class Command(BaseCommand):
    help = "Seed Requirement and SubElement compliance database from canonical KB JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Wipe existing Requirement and SubElement entries before seeding.',
        )
        parser.add_argument(
            '--file',
            type=str,
            default=None,
            help='Path to custom KB JSON file. Defaults to backend/data/canonical_kb.json.',
        )

    def handle(self, *args, **options):
        clear_existing = options['clear']
        json_file_path = options['file']

        if not json_file_path:
            json_file_path = os.path.join(settings.BASE_DIR, 'data', 'canonical_kb.json')
        else:
            if not os.path.isabs(json_file_path):
                json_file_path = os.path.abspath(json_file_path)

        if not os.path.exists(json_file_path):
            raise CommandError(f"Canonical KB file not found at path: {json_file_path}")

        self.stdout.write(self.style.NOTICE(f"Loading Knowledge Base dataset from: {json_file_path}"))

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
        except Exception as e:
            raise CommandError(f"Failed to parse JSON file {json_file_path}: {str(e)}")

        if not isinstance(kb_data, list):
            raise CommandError("Expected JSON root to be a list of requirement objects.")

        with transaction.atomic():
            if clear_existing:
                sub_del_count, _ = SubElement.objects.all().delete()
                req_del_count, _ = Requirement.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Cleared existing KB records: {req_del_count} Requirements, {sub_del_count} SubElements deleted."
                    )
                )

            req_created_count = 0
            req_updated_count = 0
            sub_created_count = 0
            sub_updated_count = 0
            sub_deleted_count = 0

            for entry in kb_data:
                citation = entry.get('statute_citation')
                if not citation:
                    self.stderr.write(self.style.ERROR("Skipping entry missing 'statute_citation'"))
                    continue

                defaults = {
                    'title': entry.get('title', ''),
                    'description': entry.get('description', ''),
                    'taxonomy_type': entry.get('taxonomy_type', 'existence'),
                    'penalty_tier': entry.get('penalty_tier', 'medium'),
                    'mandatory_weight': entry.get('mandatory_weight', 1.0),
                    'threshold_value': entry.get('threshold_value'),
                    'threshold_unit': entry.get('threshold_unit'),
                    'threshold_op': entry.get('threshold_op'),
                    'domain': entry.get('domain', 'labour'),
                }

                req, created = Requirement.objects.update_or_create(
                    statute_citation=citation,
                    defaults=defaults,
                )

                if created:
                    req_created_count += 1
                else:
                    req_updated_count += 1

                # Sync SubElements
                sub_elements_data = entry.get('sub_elements', [])
                current_keys = []

                for sub_entry in sub_elements_data:
                    element_key = sub_entry.get('element_key')
                    if not element_key:
                        continue
                    current_keys.append(element_key)

                    sub_defaults = {
                        'element_text': sub_entry.get('element_text', ''),
                        'weight': sub_entry.get('weight', 1.0),
                        'gliner_label': sub_entry.get('gliner_label'),
                    }

                    sub_obj, sub_created = SubElement.objects.update_or_create(
                        requirement=req,
                        element_key=element_key,
                        defaults=sub_defaults,
                    )

                    if sub_created:
                        sub_created_count += 1
                    else:
                        sub_updated_count += 1

                # Clean up orphaned SubElements no longer in JSON for this requirement
                orphaned = req.sub_elements.exclude(element_key__in=current_keys)
                orphaned_count = orphaned.count()
                if orphaned_count > 0:
                    orphaned.delete()
                    sub_deleted_count += orphaned_count

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded Knowledge Base!\n"
                f"  Requirements: {req_created_count} created, {req_updated_count} updated\n"
                f"  SubElements:  {sub_created_count} created, {sub_updated_count} updated, {sub_deleted_count} orphaned deleted"
            )
        )
