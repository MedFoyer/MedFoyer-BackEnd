def combine_names(item):
    item["name"] = item["given_name"] + " " + item["last_name"]
    item.pop("given_name")
    item.pop("last_name")
    return item