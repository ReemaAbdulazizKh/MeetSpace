EMPLOYEES = [
    {'id': 'sara', 'display_name': {'ar': 'سارة أحمد', 'en': 'Sarah Ahmed'}},
    {'id': 'noura', 'display_name': {'ar': 'نورة محمد', 'en': 'Noura Mohammed'}},
    {'id': 'fahad', 'display_name': {'ar': 'فهد علي', 'en': 'Fahad Ali'}},
]
ROOMS = []
for prefix, kind, ar, en, capacities in [
    ('T', 'training', 'قاعة التدريب', 'Training Room', [10, 15, 15, 20, 30]),
    ('M', 'meeting', 'قاعة الاجتماعات', 'Meeting Room', [6, 6, 10, 10, 15]),
]:
    for number, capacity in enumerate(capacities, 1):
        ROOMS.append({'id': f'{prefix}{number:02}',
                      'name': {'ar': f'{ar} {number:02}', 'en': f'{en} {number:02}'},
                      'type': kind, 'capacity': capacity, 'status': 'available'})
