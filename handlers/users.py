import boto3
import os

cognito_client = boto3.client('cognito-idp')
user_pool_id = os.environ.get("USER_POOL_ID")

def is_admin(username):
    response = cognito_client.admin_list_groups_for_user(Username=username,
                                              UserPoolId=user_pool_id)
    groups = response["Groups"]
    return any(group["GroupName"] == "sys-admin" for group in groups)

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

    attributes = response["User"]["Attributes"]
    email_attribute = next((attr for attr in attributes if attr["Name"] == "email"), None)

    return {"username" : response["User"]["Username"],
            "email" : email_attribute["Value"],
            "is_admin" : False}

def delete_user_handler(event, context):
    username = event["username"]
    clinic_id = event["clinic_id"]
    try:
        response = cognito_client.admin_get_user(UserPoolId=user_pool_id,
                                                 Username=username)
        attributes = response["UserAttributes"]
        clinic_id_attribute = next((attr for attr in attributes if attr["Name"] == "custom:clinic_id"), None)
        email_attribute = next((attr for attr in attributes if attr["Name"] == "email"), None)
        admin_status = is_admin(username)
        if clinic_id_attribute["Value"] != clinic_id:
            raise RuntimeError(f"Username {username} doesn't exists!")
        cognito_client.admin_delete_user(UserPoolId=user_pool_id,
                                         Username=username)
        return {"username" : response["Username"],
                "email" : email_attribute["Value"],
                "is_admin" : admin_status}
    except cognito_client.exceptions.UserNotFoundException:
        raise RuntimeError(f"Username {username} doesn't exists!")

def make_user_sys_admin_handler(event, context):
    username = event["username"]
    clinic_id = event["clinic_id"]
    try:
        response = cognito_client.admin_get_user(UserPoolId=user_pool_id,
                                                 Username=username)
        attributes = response["UserAttributes"]
        clinic_id_attribute = next((attr for attr in attributes if attr["Name"] in ["custom:clinic_id", "custom:clinic_ident"]), None)
        email_attribute = next((attr for attr in attributes if attr["Name"] == "email"), None)
        if clinic_id_attribute["Value"] != clinic_id:
            raise RuntimeError(f"Username {username} doesn't exists!")
        cognito_client.admin_add_user_to_group(UserPoolId=user_pool_id,
                                               Username=username,
                                               GroupName='sys-admin')
        return {"username" : response["Username"],
                "email" : email_attribute["Value"],
                "is_admin" : True}
    except cognito_client.exceptions.UserNotFoundException:
        raise RuntimeError(f"Username {username} doesn't exists!")

def remove_user_from_sys_admins_handler(event, context):
    username = event["username"]
    clinic_id = event["clinic_id"]
    try:
        response = cognito_client.admin_get_user(UserPoolId=user_pool_id,
                                                 Username=username)
        attributes = response["UserAttributes"]
        clinic_id_attribute = next((attr for attr in attributes if attr["Name"] == "custom:clinic_id"), None)
        email_attribute = next((attr for attr in attributes if attr["Name"] == "email"), None)
        if clinic_id_attribute["Value"] != clinic_id:
            raise RuntimeError(f"Username {username} doesn't exists!")
        cognito_client.admin_remove_user_from_group(UserPoolId=user_pool_id,
                                               Username=username,
                                               GroupName='sys-admin')
        return {"username" : response["Username"],
                "email" : email_attribute["Value"],
                "is_admin" : False}
    except cognito_client.exceptions.UserNotFoundException:
        raise RuntimeError(f"Username {username} doesn't exists!")