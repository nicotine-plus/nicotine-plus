import pickle

with open('data/login/socket_localhost:22420.log', 'rb') as f:
    logs = pickle.load(f, encoding='bytes')

logs_chronologically = {}
for mode in b'send', b'recv':
    for time, event in logs[b'transactions'][mode].items():
        logs_chronologically[time] = (mode.decode('latin1'), event)

for time, event in logs_chronologically.items():
    print(f"{time} {event[0]}: {event[1][:100]}")
