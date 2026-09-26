from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Inspect the database schema for the home_article table'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'home_article'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                self.stdout.write(self.style.ERROR('Table home_article does not exist'))
                return
                
            # Get table columns
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'home_article';
            """)
            columns = cursor.fetchall()
            
            self.stdout.write(self.style.SUCCESS('Columns in home_article table:'))
            self.stdout.write('-' * 80)
            for col in columns:
                self.stdout.write(f"{col[0]:<20} {col[1]:<20} Nullable: {col[2]:<5} Default: {col[3] or 'None'}")
            
            # Check specific fields
            column_names = [col[0] for col in columns]
            self.stdout.write('\nField status:')
            self.stdout.write(f"is_published exists: {'is_published' in column_names}")
            self.stdout.write(f"published exists: {'published' in column_names}")
            self.stdout.write(f"is_deleted exists: {'is_deleted' in column_names}")
            self.stdout.write(f"deleted exists: {'deleted' in column_names}")
