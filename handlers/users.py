import boto3
import os

cognito_client = boto3.client('cognito-idp')
user_pool_id = os.environ.get("USER_POOL_ID")

def create_user_handler(event, context):
    username = event["username"]
    email = event["email"]
    clinic_id = event["clinic_id"]
    try:
        response = cognito_client.admin_create_user(UserPoolId=user_pool_id,
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
    except cognito_client.exceptions.UsernameExistsException:
        raise RuntimeError(f"Username {username} already exists!")

    return {"username" : response["User"]["Username"]}

def delete_user_handler(event, context):
    username = event["username"]
    clinic_id = event["clinic_id"]
    try:
        response = cognito_client.admin_get_user(UserPoolId=user_pool_id,
                                                 Username=username)
        attributes = response["UserAttributes"]
        clinic_id_attribute = next((attr for attr in attributes if attr["Name"] == "custom:clinic_id"), None)
        if clinic_id_attribute["Value"] != clinic_id:
            raise RuntimeError(f"Username {username} doesn't exists!")
        cognito_client.admin_delete_user(UserPoolId=user_pool_id,
                                         Username=username)
        return {"username" : response["User"]["Username"]}
    except cognito_client.exceptions.UserNotFoundException:
        raise RuntimeError(f"Username {username} doesn't exists!")