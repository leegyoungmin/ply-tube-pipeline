def preprocess(item):
    item = item.lower()
    
    item_split = item.split('-')
    if len(item_split) == 2:
        item_split = list(map(lambda x: x.replace(' ',''), item_split))
        item = ' - '.join(item_split)
    return item