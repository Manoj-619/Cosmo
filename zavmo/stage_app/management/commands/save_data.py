from django.core.management.base import BaseCommand
import pandas as pd
from stage_app.models import NOS, JobDescription, OFQUAL

class Command(BaseCommand):
    help = 'Saves NOS and Job Description data from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to Excel file containing NOS and JD data')

    def handle(self, *args, **options):
        file_path = options['file_path']
        try:
            # Read both sheets from the Excel file
            nos_df    = pd.read_excel(file_path, sheet_name='NOS model')
            jd_df     = pd.read_excel(file_path, sheet_name='JD model')
            ofqual_df = pd.read_excel(file_path, sheet_name='OFQUAL model')

            # Bulk create NOS objects
            nos_to_create = []
            
            for _, row in nos_df.iterrows():
                if not NOS.objects.filter(nos_id=row['nos_id']).exists():
                    nos_to_create.append(NOS(
                            nos_id=row['nos_id'],
                            text=row['text'],
                            industry=row['industry']
                        ))
                else:
                    self.stdout.write(self.style.WARNING(f'NOS {row["nos_id"]} already exists in the NOS table'))
            
            # Bulk create new NOS objects
            created_nos = NOS.objects.bulk_create(nos_to_create)
            self.stdout.write(self.style.SUCCESS(f'Successfully saved {len(created_nos)} new NOS records\n'))

            # Bulk create OFQUAL objects first
            ofqual_objects = []
            for _, row in ofqual_df.iterrows():
                if not OFQUAL.objects.filter(ofqual_id=row['ofqual_id']).exists():
                    ofqual_objects.append(OFQUAL(
                        ofqual_id=row['ofqual_id'],
                        level=row['level'],
                        text=row['text'],
                        markscheme=row['markscheme']
                    ))
                else:
                    self.stdout.write(self.style.WARNING(f'OFQUAL {row["ofqual_id"]} already exists in the OFQUAL table'))
            created_ofqual = OFQUAL.objects.bulk_create(ofqual_objects)
            self.stdout.write(self.style.SUCCESS(f'Successfully saved {len(created_ofqual)} new OFQUAL records'))

            # Bulk create JD objects first
            jd_objects = []
            for _, row in jd_df.iterrows():
                if not JobDescription.objects.filter(job_role=row['job_role']).exists():
                    jd_objects.append(JobDescription(
                        job_role=row['job_role'],
                        description=row['main_purpose'],
                        responsibilities=row['responsibilities']
                    ))
                else:
                    self.stdout.write(self.style.WARNING(f'Job Description {row["job_role"]} already exists in the JobDescription table'))
            created_jds = JobDescription.objects.bulk_create(jd_objects)

            # Now iterate and add NOS relationships
            for jd, row in zip(created_jds, jd_df.itertuples()):
                nos_ids = str(row.nos_ids) if pd.notna(row.nos_ids) else ''
                nos_ids = [id.strip() for id in nos_ids.split(',')] if nos_ids else []
                jd.nos.add(*NOS.objects.filter(nos_id__in=nos_ids))

            for jd, row in zip(created_jds, jd_df.itertuples()):
                ofqual_ids = str(row.ofqual_ids) if pd.notna(row.ofqual_ids) else ''
                ofqual_ids = [id.strip() for id in ofqual_ids.split(',')] if ofqual_ids else []
                jd.ofqual.add(*OFQUAL.objects.filter(ofqual_id__in=ofqual_ids))

            self.stdout.write(self.style.SUCCESS(f'Successfully saved {len(jd_df)} Job Description, NOS and OFQUAL records'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error saving data: {str(e)}'))