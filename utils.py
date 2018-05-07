import boto3
import json

DEFAULT_BUCKET = "kuvrr-analytics-test"
session = boto3.Session(profile_name='agimage')


def get_s3_file(key, bucket=DEFAULT_BUCKET):
    #client = boto3.client('s3')
    client = session.client('s3')

    try:
        response = client.get_object(
            Bucket = bucket,
            Key = key
        )

        print (response)
        return response

    except:
        print("File not found on S3 for key: " + key)
        return None


def save_data(key, body, content_type, bucket=DEFAULT_BUCKET):

    print('Saving data to: ' + key + ' bucket: ' + bucket)

    #client = boto3.client('s3')
    client = session.client('s3')


    try:
        response = client.put_object(
            Bucket = bucket,
            Key = key,
            Body = body,
            ContentType = content_type
        )

    except Exception as e:
        print("Error saving file to S3: " + str(e))


# Test harnesses
#get_s3_file('test-images/Birds.jpg')
#body = {
#'name':'jaison',
#'game': 'badi'
#}

#save_data('test.json',json.dumps(body),'application/json')