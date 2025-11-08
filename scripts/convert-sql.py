import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to keyword.txt, which is in the parent directory
keyword_file_path = os.path.join(script_dir, 'keyword.txt')

with open(keyword_file_path, "r", encoding="utf-8") as f:
    lines = set(line.strip() for line in f if line.strip())

#sql = "INSERT INTO keyword (keyword) VALUES\n" + ",\n".join(f"('{line}')" for line in sorted(lines)) + "\nON CONFLICT (keyword) DO NOTHING;"
sql = "INSERT INTO keyword (keyword) VALUES\n" + ",\n".join(f"('{line}')" for line in sorted(lines)) + ";"


with open(os.path.join(script_dir, "insert.sql"), "w", encoding="utf-8") as out:
    out.write(sql)