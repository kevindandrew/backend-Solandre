import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("Error: DATABASE_URL not found in environment variables.")
    exit(1)

def add_column_if_not_exists(engine, table_name, column_name, column_type):
    with engine.connect() as connection:
        # Check if column exists
        check_query = text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='{table_name}' AND column_name='{column_name}';
        """)
        result = connection.execute(check_query).fetchone()
        
        if not result:
            print(f"Adding column '{column_name}' to table '{table_name}'...")
            alter_query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")
            connection.execute(alter_query)
            connection.commit()
            print(f"Column '{column_name}' added successfully.")
        else:
            print(f"Column '{column_name}' already exists in table '{table_name}'.")

def main():
    print(f"Connecting to database...")
    engine = create_engine(DATABASE_URL)
    
    # Add imagen_url to platos
    add_column_if_not_exists(engine, "platos", "imagen_url", "VARCHAR(255)")
    
    # Add imagen_url to menu_dia
    add_column_if_not_exists(engine, "menu_dia", "imagen_url", "VARCHAR(255)")
    
    print("Migration completed.")

if __name__ == "__main__":
    main()
