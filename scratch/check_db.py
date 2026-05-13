import os
import sys
import django
from pathlib import Path

# Set up paths
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_test.settings')
django.setup()

from django.db import connection

print(f"Connecting to: {connection.settings_dict.get('NAME')}")
print(f"Engine: {connection.settings_dict.get('ENGINE')}")

try:
    with connection.cursor() as cursor:
        print("Checking column info...")
        cursor.execute("""
            SELECT column_name, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'app_testregistration' AND column_name = 'question_paper_id';
        """)
        row = cursor.fetchone()
        if row:
            print(f"Column: {row[0]}, Is Nullable: {row[1]}")
            if row[1] == 'NO':
                print("❌ Column is NOT NULL. Attempting to fix with raw SQL...")
                cursor.execute("ALTER TABLE app_testregistration ALTER COLUMN question_paper_id DROP NOT NULL;")
                print("✅ Altered column successfully.")
            else:
                print("✅ Column is already NULLABLE.")
        else:
            print("❌ Column 'question_paper_id' not found in 'app_testregistration'!")
            
            # Check table existence
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            tables = cursor.fetchall()
            print(f"Available tables: {[t[0] for t in tables]}")
            
except Exception as e:
    print(f"❌ Error: {e}")
