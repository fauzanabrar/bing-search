import re

# Parse keywords_called.txt and find keywords to remove
to_remove = set()
called_lines = []
with open('keywords_called.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.rstrip('\n')
        m = re.match(r'^(.*?):(\d+)$', line)
        if m:
            keyword, count = m.group(1), int(m.group(2))
            if count >= 6:
                to_remove.add(keyword)
            else:
                called_lines.append(line)
        else:
            called_lines.append(line)

# Remove from keywords.txt
with open('keywords.txt', 'r', encoding='utf-8') as f:
    keywords = [line.strip() for line in f if line.strip()]
filtered_keywords = [kw for kw in keywords if kw not in to_remove]
with open('keywords.txt', 'w', encoding='utf-8') as f:
    for kw in filtered_keywords:
        f.write(kw + '\n')

# Remove from keywords_called.txt (only lines with keyword:counter)
with open('keywords_called.txt', 'w', encoding='utf-8') as f:
    for line in called_lines:
        # Remove lines with keyword:counter if keyword in to_remove
        m = re.match(r'^(.*?):(\d+)$', line)
        if m and m.group(1) in to_remove:
            continue
        f.write(line + '\n')

print(f"Removed {len(to_remove)} keywords from both files.")