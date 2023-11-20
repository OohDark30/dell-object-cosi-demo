import boto3


# set connection sample code
def getConnection(host, secure, accesskey, secretkey) -> boto3.client:

    # host address
    # ECS runs S3 with SSL/TLS on 9021 and plaintext on 9020.  If you're behind a load balancer this will usually be
    # remapped to 80/443.
    host = host
    secure = secure
    # Your AWS access key ID is also known in ECS as your object user
    access_key_id = accesskey
    # The secret key that belongs to your object user.
    secret_key = secretkey

    s3 = boto3.client('s3', aws_access_key_id=access_key_id, aws_secret_access_key=secret_key, use_ssl=secure,
                      endpoint_url=host)
    # boto3.client
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#client
    return s3

