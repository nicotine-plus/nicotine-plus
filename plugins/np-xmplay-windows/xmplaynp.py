# 'Request' example added jjk  11/20/98

if __name__ == "__main__":
	import win32ui
	import dde

	from sys import argv
	layout = "%artist - %title [%album] %haha"
	if len(argv) > 1:
		layout = argv[1]
	
	server = dde.CreateServer()
	server.Create("nicotine")
	conversation = dde.CreateConversation(server)
	info = {}
	conversation.ConnectTo("xmplay", "info0")
	reply = conversation.Request("info0")
	for tuple in reply.split('\n'):
		(item, tab, value) = tuple.partition('\t')
		item = item.strip()
		if item:
			info[item.lower()] = value
	conversation.ConnectTo("xmplay", "info1")
	reply = conversation.Request("info1")
	for tuple in reply.split('\n'):
		(item, tab, value) = tuple.partition('\t')
		item = item.strip()
		if item:
			info[item.lower()] = value
		
	keys = info.keys()
	keys.sort(reverse = True, key = len)
	for key in keys:
		value = info[key]
		layout = layout.replace("%" + key, value)
	print layout