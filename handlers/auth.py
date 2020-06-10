#This function is used by Cognito to add the clinic ID to the JWT claims
def claim_add_handler(event, context):
    attributes = event["request"]["userAttributes"]
    clinic_id = attributes.get("custom:clinic_ident", None)
    if clinic_id:
        event["response"]["claimsOverrideDetails"] = {
            "claimsToAddOrOverride" : {
                "clinic_id": clinic_id
            }
        }
    return event