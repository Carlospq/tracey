from django.template.defaulttags import register

# Custom template filter to get data from a dictionary using key in template

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='splitAlignment')
def splitAlignment(value, key):
    value = [ [y for y in x] for x in str(value).split("\n")]
    return value

@register.filter
def index(indexable, i):
    return indexable[i]


@register.filter
def split_str(splitable, positions):
    print(positions)
    start, stop = [int(x) for x in positions.split(",")]
    return splitable[start:stop]


@register.filter
def has_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()