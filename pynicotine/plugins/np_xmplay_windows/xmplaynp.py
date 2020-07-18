if __name__ == "__main__":
    import dde

    from sys import argv
    layout = "{%artist - }{%title }{[%album]}"
    if len(argv) > 1:
        layout = argv[1]
    layout = layout.replace('{', '{{').replace('}', '}}')  # double curly brackets are not that likely to exist in tags
    optionals = []  # Elements in this list will be removed from the output
    open = -2
    while open == -2 or open > -1:
        open = layout.find('{{', open + 2)
        close = layout.find('}}', open + 2)
        if close > -1:
            optionals.append(layout[open:close + 2])

    server = dde.CreateServer()
    server.Create("xmplaynp")
    conversation = dde.CreateConversation(server)
    info = {}
    conversation.ConnectTo("xmplay", "info0")
    reply = conversation.Request("info0")
    for tuple in reply.split('\n'):
        parts = tuple.split('\t', 1)
        item = parts[0].strip()
        if item:
            info[item.lower()] = value  # noqa: F821
    conversation.ConnectTo("xmplay", "info1")
    reply = conversation.Request("info1")
    for tuple in reply.split('\n'):
        parts = tuple.split('\t', 1)
        item = parts[0].strip()
        if item:
            info[item.lower()] = value  # noqa: F821

    keys = list(info.keys())
    keys.sort(reverse=True, key=len)
    for key in keys:
        value = info[key]
        layout = layout.replace("%" + key, value)
    # Removing optional fields that weren't replaced
    for optional in optionals:
        layout = layout.replace(optional, '')
    # And now removing the brackers of filled in fields
    layout = layout.replace('{{', '').replace('}}', '')
    print(layout)
