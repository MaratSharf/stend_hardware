import csv
with open('tools.csv', 'r', encoding='cp1251', newline='') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i < 3:
            print(f'Row {i}: tool_id={row["tool_id"]}, category_ru={row["category_ru"]}, name_ru={row["name_ru"]}')
        else:
            break
print('Total rows:', sum(1 for _ in open('tools.csv', 'r', encoding='utf-8')) - 1)
