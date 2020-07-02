#WARNING: Don't change primary keys in any transform.
# If you do, it will cause new records to be created without any change to the old ones

def combine_names(item):
    item["name"] = item["given_name"] + " " + item["last_name"]
    item.pop("given_name")
    item.pop("last_name")
    return item