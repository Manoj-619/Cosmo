from django.core.management.base import BaseCommand
import pandas as pd
from stage_app.models import NOS, JobDescription

class Command(BaseCommand):
    help = 'Saves NOS and Job Description data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to Excel file containing NOS and JD data')

    def handle(self, *args, **options):
        file_path = options['file_path']
        try:
            # Read both sheets from the Excel file
            nos_df = pd.read_excel(file_path, sheet_name='NOS model')
            jd_df  = pd.read_excel(file_path, sheet_name='JD model')

            # Bulk create NOS objects
            nos_to_create = []
            existing_nos = {nos.nos_id: nos for nos in NOS.objects.all()}
            
            for _, row in nos_df.iterrows():
                if row['nos_id'] not in existing_nos:
                    nos_to_create.append(NOS(
                        nos_id=row['nos_id'],
                        performance_criteria=row['performance_criteria'],
                        knowledge_criteria=row['knowledge_criteria'],
                        text=row['text'],
                        industry=row['industry']
                    ))
            
            # Bulk create new NOS objects
            created_nos = NOS.objects.bulk_create(nos_to_create)
            self.stdout.write(self.style.SUCCESS(f'Successfully saved {len(created_nos)} new NOS records'))

            # Bulk create JD objects first
            jd_objects = []
            for _, row in jd_df.iterrows():
                jd_objects.append(JobDescription(
                    job_role=row['job_role'],
                    description=row['main_purpose'],
                    responsibilities=row['responsibilities']
                ))
            created_jds = JobDescription.objects.bulk_create(jd_objects)

            # Now iterate and add NOS relationships
            for jd, row in zip(created_jds, jd_df.itertuples()):
                nos_ids = row.nos_id.split(',')
                nos_ids = [id.strip() for id in nos_ids]
                self.stdout.write(self.style.SUCCESS(f'Found {len(nos_ids)} NOS records for {row.job_role}'))
                jd.nos.add(*NOS.objects.filter(nos_id__in=nos_ids))

            self.stdout.write(self.style.SUCCESS(f'Successfully saved {len(jd_df)} Job Description records'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error saving data: {str(e)}'))