from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from stage_app.models import Org, UserProfile, FourDSequence, TNAassessment

class Command(BaseCommand):
    help = 'Creates test users and associates them with an organization'

    def handle(self, *args, **kwargs):
        # Create or get organization
        org, created = Org.objects.get_or_create(
            org_id="zav-4323",
            org_name="Zavmo AI"
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created organization: {org.org_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Organization already exists: {org.org_name}'))

        # Create users
        for i in range(1, 101):
            email = f"iridescenttestuser_{i}@test.com"
            
            # Create user if doesn't exist
            user, user_created = User.objects.get_or_create(
                email=email,
                defaults={'username': email}
            )
            
            if user_created:
                # Create UserProfile
                UserProfile.objects.create(user=user, org=org)
                
                # Create FourDSequence
                FourDSequence.objects.create(user=user)
                
                self.stdout.write(self.style.SUCCESS(f'Created user: {email}'))
            else:
                self.stdout.write(self.style.WARNING(f'User already exists: {email}'))