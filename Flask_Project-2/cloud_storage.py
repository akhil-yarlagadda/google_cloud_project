import os,datetime
import json

from flask import Flask, render_template, redirect, request, send_file,flash
from werkzeug.utils import secure_filename

from PIL import Image
from PIL.ExifTags import TAGS

from google.cloud import storage
from google.cloud import datastore
from google.cloud import secretmanager
from google.oauth2 import service_account
from google.auth import exceptions

app = Flask(__name__)
app.config['SECRET_KEY']='sri_ushodaya'

@app.route('/')
def home():
    images=[]
    for file in list_files():
        images.append(file)
    return render_template('home_cloud.html',images=images)


def access_secret_version(project_id,secret_id,version_id):
    client_secretkey=secretmanager.SecretManagerServiceClient()
    name=f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response=client_secretkey.access_secret_version(request={"name":name})
    return response.payload.data.decode("UTF-8")

project_id='civil-willow-398118' #'6658778261'
secret_id='first-project-secretkey'
version_id=1
bucket_name="first-project-bucket-akhily"
try:
    secret_value=access_secret_version(project_id,secret_id,version_id)
    auth_credentials=service_account.Credentials.from_service_account_info(json.loads(secret_value))
    storage_client = storage.Client(credentials=auth_credentials)
    client=datastore.Client(credentials=auth_credentials)
except exceptions.DefaultCredentialsError as e:
    print(f"DefaultCredentialsError:{e}")
    raise
except Exception as e:
    print(f"An unexpected error occurred:{e}")


@app.route('/upload',methods=['POST'])
def upload():
    file = request.files['form_file']
    if file.filename == '':
        flash('*No File Selected')
        return redirect("/")
    else:
        k=upload_to_bucket(file.filename,file)
        l=upload_metadata_into_datastore(file)
        return redirect("/")
    
@app.route('/image/<filename>')
def get_file(filename):
    data=get_metadata_from_datastore(filename)
    blob=get_blob_from_bucket(bucket_name,filename)
    if blob:
        expiration_time = datetime.datetime.utcnow()+datetime.timedelta(hours=1)
        signed_url=blob.generate_signed_url(expiration=expiration_time)
        return render_template('file_metadata.html',image_url=signed_url,img_filename=filename,dict_val=data)
    else:
        return "Image not found",404   

def list_files():
    blobs = storage_client.list_blobs(bucket_name)
    jpegs = []
    for blob in blobs:
        if blob.name.endswith(".jpeg") or blob.name.endswith(".jpg"):
            jpegs.append(blob.name)
            #print(blob.name)
    return jpegs

def upload_to_bucket(blob_name,blob_file):
    try:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_file(blob_file)
        return True
    except Exception as e:
        print(e)
        return False

def get_blob_from_bucket(bucket_name,file_name):
    try:
        bucket=storage_client.get_bucket(bucket_name)
        blob=bucket.blob(file_name)
        return blob
    except exceptions.GoogleAuthError as e:
        print(f"Error:{e}")
        return None

def upload_metadata_into_datastore(file):
    with Image.open(file) as img:
            exifdata = img.getexif()
    if exifdata:
         with client.transaction():
             keys=client.key("imagemetadata")
             metadata_rows = datastore.Entity(key=keys)
             metadata_rows['filename']=file.filename
             for tagid in exifdata:
                tagname = TAGS.get(tagid,tagid)
                value=exifdata.get(tagid)
                metadata_rows[str(tagname)]=str(value)
             client.put(metadata_rows)
         return True
    else:
        return "No Exif metadata"

def get_metadata_from_datastore(filename):
    query=client.query(kind='imagemetadata')
    query.add_filter("filename","=",filename)
    entities = list(query.fetch())
    metadata_val={}
    for key,value in entities[0].items():
        metadata_val[key]=value
    return metadata_val
    
if __name__=='__main__':
    app.run(host='0.0.0.0',port=8080)

