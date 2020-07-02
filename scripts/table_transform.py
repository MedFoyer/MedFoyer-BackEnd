import boto3
import argparse
import time
import helpers.transforms as transforms

def scan_records(table, transform):
    page_key = None
    with table.batch_writer() as batch:
        while True:

            response = table.scan(ExclusiveStartKey = page_key) if page_key else table.scan()
            page_key = response.get("LastEvaluatedKey")
            items = response["Items"]
            for item in items:
                transformed = transform(item)
                batch.put_item(Item=transformed)
            if not page_key:
                break
            #pause here to avoid consuming too much dynamo capacity TODO: make this configurable
            time.sleep(10)


parser = argparse.ArgumentParser(description="Simple script to scan through a single table and apply a transform to each item.")
parser.add_argument("table", type=str, help="The table name")
parser.add_argument("transform", type=str, help="Function name of the transform, found in helpers/transforms.py")
#TODO: add some sort of filter for cases where we don't need to look at every item in the table

args = parser.parse_args()
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(args.table)
transform = getattr(transforms, args.transform)
scan_records(table, transform)