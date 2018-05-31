import boto3
import os

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

    print ('Success')

def save_file(file, bucket, folder):

    print('Saving file to: bucket: ' + bucket)

    #client = boto3.client('s3')
    client = session.client('s3')
    filename = folder + os.path.basename(file)

    try:
        client.upload_file(file, bucket, filename)

    except Exception as e:
        print("Error saving file to S3: " + str(e))

    print ('Success')

class manifest_file():

    def __init__(self, fname):
        self.fname = fname
        self.manifest = []
        self.initial_length = self.file_len()
        self.last_length = self.initial_length[1]

    def file_len(self):
        i = -1
        with open(self.fname) as f:
            for i, l in enumerate(f):
                self.manifest.append(l)
        return i + 1, i + 1

    def diff_file_len(self):

        i = self.last_length - 1
        start = i
        # print ('start',start)
        with open(self.fname) as f:
            for i, l in enumerate(f):
                if i > start:
                    self.manifest.append(l)
        self.last_length = i + 1
        if i + 1 >= 1:
            if start < 0:
                # print('here 1')
                return 1, i + 1
            else:
                # print('here 2')
                if start + 2 > i + 1:
                    return i + 1, i + 1
                else:
                    return start + 2, i + 1
        else:
            return 0, 0

    def set_last_length(self, length):
        self.last_length = length

    def get_last_length(self):
        return self.last_length

    def get_initial_length(self):
        return self.initial_length




            # Test harnesses
#get_s3_file('test-images/Birds.jpg')
# body = {
# 'name':'jaison',
# 'game': 'badi'
# }

#save_data('test.json',json.dumps(body),'application/json')

#save_file('./static/kvs/test.mkv_rawfile0.mkv', 'kuvrr-analytics-test', 'static/')