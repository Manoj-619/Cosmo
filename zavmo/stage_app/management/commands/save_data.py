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
            created_job_roles = []  # Track which job roles we're creating
            for _, row in jd_df.iterrows():
                if not JobDescription.objects.filter(job_role=row['job_role']).exists():
                    jd_objects.append(JobDescription(
                        job_role=row['job_role'],
                        description=row['main_purpose'],
                        responsibilities=row['responsibilities']
                    ))
                    created_job_roles.append(row['job_role'])  # Add to our tracking list
                else:
                    self.stdout.write(self.style.WARNING(f'Job Description {row["job_role"]} already exists in the JobDescription table'))
            created_jds = JobDescription.objects.bulk_create(jd_objects)
            self.stdout.write(self.style.SUCCESS(f'Successfully created {len(created_jds)} new Job Description records'))

            # Process NOS and OFQUAL relationships for all job descriptions in the dataframe
            for _, row in jd_df.iterrows():
                try:
                    # Get or skip the job description
                    try:
                        jd = JobDescription.objects.get(job_role=row['job_role'])
                    except JobDescription.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Could not find job description for {row["job_role"]}'))
                        continue
                    
                    # Process NOS relationships
                    if 'nos_ids' in row and pd.notna(row['nos_ids']):
                        nos_ids = str(row['nos_ids'])
                        nos_ids = [id.strip() for id in nos_ids.split(',') if id.strip()]
                        print(f"NOS IDs: {nos_ids}")
                        if nos_ids:
                            nos_objects = NOS.objects.filter(nos_id__in=nos_ids)
                            if nos_objects.exists():
                                jd.nos.set(nos_objects)
                            else:
                                self.stdout.write(self.style.WARNING(f'No NOS objects found for IDs: {nos_ids}'))
                    
                    # Process OFQUAL relationships
                    if 'ofqual_ids' in row and pd.notna(row['ofqual_ids']):
                        ofqual_ids = str(row['ofqual_ids'])
                        ofqual_ids = [id.strip() for id in ofqual_ids.split(',') if id.strip()]
                        print(f"OFQUAL IDs: {ofqual_ids}")
                        if ofqual_ids:
                            ofqual_objects = OFQUAL.objects.filter(ofqual_id__in=ofqual_ids)
                            
                            if ofqual_objects.exists():
                                jd.ofqual.set(ofqual_objects)
                            else:
                                self.stdout.write(self.style.WARNING(f'No OFQUAL objects found for IDs: {ofqual_ids}'))
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error processing relationships for {row["job_role"]}: {str(e)}'))

            self.stdout.write(self.style.SUCCESS(f'Successfully processed {len(jd_df)} Job Description records with NOS and OFQUAL relationships'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error saving data: {str(e)}'))