def to_tree(items):
    def children(parent_id):
       return map(lambda i: {**i, **dict(children=list(children(i['ID'])))}, filter(lambda i: i.get('ParentGroup', {}).get('ID',0) == parent_id, items))
    return list(children(0))
