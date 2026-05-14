import os
print('exists:', os.path.exists('tools.csv'))
if os.path.exists('tools.csv'):
    raw = open('tools.csv', 'rb').read(100)
    print('first bytes:', raw)
    for enc in ['utf-8', 'cp1251', 'utf-16', 'latin1']:
        try:
            decoded = raw.decode(enc)
            print('encoding:', enc, '->', decoded[:50])
        except:
            pass
