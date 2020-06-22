import boto3
import os

cognito_client = boto3.client('cognito-idp')
user_pool_id = os.environ.get("USER_POOL_ID")

def create_user_handler(event, context):
    username = event["username"]
    email = event["email"]
    clinic_id = event["clinic_id"]
    #TODO: Determine if we need to do an existence check first
    response = cognito_client.admin_create_user(UserPoolId="user_pool_id",
                                     Username=username,
                                     UserAttributes=[
                                         {
                                             'Name': "email",
                                             'Value': email
                                         },
                                         {
                                             'Name': "custom:clinic_id",
                                             'Value': clinic_id
                                         }
                                     ])

    return {"username" : response["User"]["Username"]}