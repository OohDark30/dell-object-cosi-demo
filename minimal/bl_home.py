import string
from io import BytesIO

from flask import (
    Blueprint, render_template, request, send_from_directory, flash, url_for
)
from .layoutUtils import *
from .auth import *
import os
import json
import urllib.parse
from minimal.s3 import GetConnection
import logging
from botocore.exceptions import ClientError

bp = Blueprint('bl_home', __name__)

@bp.route('/', methods=('GET', 'POST'))
@manage_cookie_policy
def index():
    results = {}
    error=0
    basedir = os.path.abspath(os.path.dirname('/data/cosi/'))

    if request.method == 'POST':
        cosisecret = request.form['cosisecret']
        if not cosisecret:
            flash("Msg3")
            return redirect(url_for('bl_home.index'))
        else:
            s3_secret_file = os.path.join(basedir, cosisecret)
            if not os.path.exists(s3_secret_file):
                flash("Msg4")
                return redirect(url_for('bl_home.index'))
            else:
                # We found the COS K8S Secret that should contain the bucket details lets try and parse it
                with open(s3_secret_file) as json_file:
                    data = json.load(json_file)
                    # Extract the values to display on the form

                    results["bucketclaimname"] = data["metadata"]["name"]
                    results["bucketname"] = data["spec"]["bucketName"]
                    results["endpoint"] = data["spec"]["secretS3"]["endpoint"]
                    results["accesskey"] = data["spec"]["secretS3"]["accessKeyID"]
                    results["secretkey"] = data["spec"]["secretS3"]["accessSecretKey"]
                    results["disablebuttons"] = "false"
    else:
        results["disablebuttons"] = "true"

    mc = set_menu("home") #to highlight menu option
    return render_template('home/index.html', mc=mc, results=results)


@bp.route('/about', methods=('GET', 'POST'))
@manage_cookie_policy
def about():

    mc = set_menu("about")
    return render_template('home/about.html', mc=mc)


@bp.route('/privacy-notice',methods=('GET', 'POST'))
def privacy():

    mc = set_menu("")
    return render_template('home/privacy-notice.html', mc=mc)


@bp.route('/terms-of-service',methods=('GET', 'POST'))
def termsofservice():
    mc = set_menu("")
    return render_template('home/terms-of-service.html', mc=mc)


@bp.route('/getObjects', methods=['GET', 'POST'])
def getObjects():
    results = {}
    if request.method == "POST":
        form_json_data = request.data
        form_json_data_decoded = urllib.parse.unquote(form_json_data).strip('"')

        # Convert query parameters to dictionary
        form_data = dict()
        x = form_json_data_decoded.split("&")
        for i in x:
            a, b = i.split("=")
            # assigning keys with values
            form_data[a]=b

        # Grab k8s Secret details from the form data
        bucketname = form_data['bucketname']
        bucketclaim = form_data['bucketclaim']
        endpoint = form_data['endpoint']
        accesskeyid = form_data['accesskey']
        secretkey = form_data['secretkey']

        # Enable only for testing against ECS Test Driver
        #bucketname = ''
        #endpoint = 'https://object.ecstestdrive.com'
        #accesskeyid = ''
        #secretkey = ''

        # Create boto3 s3client
        s3 = GetConnection.getConnection(endpoint, True, accesskeyid, secretkey)

        # list objects in bucketname
        s3_objects = s3.list_objects(Bucket=bucketname)

        # Generate object data in json format
        object_results_list = []

        # Initialize index
        row_id = 1

        for object_data in s3_objects['Contents']:
            # iterate through object list and if it's not a directory then add it to the list of objects
            object_list = {'id': row_id, 'Key': object_data['Key'], 'Size': object_data['Size'],
                           'Owner': object_data['Owner']['DisplayName'], 'ETag': object_data['ETag'],
                           'StorageClass': object_data['StorageClass'],
                           'LastModified': object_data['LastModified'].strftime("%Y-%m-%d %H:%M:%S")}

            if object_data['Key'][len(object_data['Key']) - 1] != '/':
                object_results_list.append(object_list)
                row_id += 1
            else:
                print("Skipping directory: " + object_data['Key'])

        # convert objects to a json string and return
        return_json = json.dumps(object_results_list, indent = 4)
        return return_json


@bp.route('/uploadObjects', methods=['POST'])
def uploadObjects():
    results = {}
    if request.method == "POST":

        try:
            form_data = request.form

            # Get the file data from the form
            form_file_data = request.files['fileupload']

            # Grab k8s Secret details from the form data
            bucketname = form_data['bucketname']
            bucketclaim = form_data['bucketclaim']
            endpoint = form_data['endpoint']
            accesskeyid = form_data['accesskey']
            secretkey = form_data['secretkey']

            # Enable only for testing against ECS Test Driver
            #bucketname = ''
            #endpoint = 'https://object.ecstestdrive.com'
            #accesskeyid = ''
            #secretkey = ''

            objectkey = form_file_data.filename
            # Create boto3 s3client
            s3 = GetConnection.getConnection(endpoint, True, accesskeyid, secretkey)

            # Read the data from the temporary file storage and upload to S3
            bytes_buffer = BytesIO(form_file_data.stream.read())
            bytes_buffer.seek(0)

            # Upload the file to S3
            response = s3.put_object(Body=bytes_buffer, Bucket=bucketname, Key=objectkey)

            # Check the response status
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                logging.error("Error uploading object: " + objectkey + " from bucket: " + bucketname + " with status code: " + str(response['ResponseMetadata']['HTTPStatusCode']))
                return "Failure"
            else:
                logging.info("Successfully uploaded object: " + objectkey + " from bucket: " + bucketname + " with status code: " + str(response['ResponseMetadata']['HTTPStatusCode']))
                return "Success"
        except ClientError as e:
            logging.error(e)
            return "Failure"


@bp.route('/deleteObjects', methods=['POST'])
def deleteObjects():
    results = {}
    if request.method == "POST":

        try:
            form_data = request.form

            # Grab object keys from the form data
            keysToDelete = form_data['keystodelete'].split(',')

            # Grab k8s Secret details from the form data
            bucketname = form_data['bucketname']
            bucketclaim = form_data['bucketclaim']
            endpoint = form_data['endpoint']
            accesskeyid = form_data['accesskey']
            secretkey = form_data['secretkey']

            # Enable only for testing against ECS Test Driver
            #bucketname = ''
            #endpoint = 'https://object.ecstestdrive.com'
            #accesskeyid = ''
            #secretkey = ''

            # Create boto3 s3client
            s3 = GetConnection.getConnection(endpoint, True, accesskeyid, secretkey)

            for objectkey in keysToDelete:
                # Delete the file from S3
                response = s3.delete_object(Bucket=bucketname, Key=objectkey)

                # Check the response status
                if response['ResponseMetadata']['HTTPStatusCode'] != 204:
                    logging.error("Error deleting object: " + objectkey + " from bucket: " + bucketname + " with status code: " + str(response['ResponseMetadata']['HTTPStatusCode']))
                    return "Failure"
                else:
                    logging.info("Successfully deleted object: " + objectkey + " from bucket: " + bucketname + " with status code: " + str(response['ResponseMetadata']['HTTPStatusCode']))

            return "Success"
        except ClientError as e:
            logging.error(e)
            return "Failure"


@bp.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        print("Data received from Webhook is: ", request.json)
        return "Webhook received!"

# MANAGE sitemap and robots calls
# These files are usually in root, but for Flask projects must
# be in the static folder
@bp.route('/robots.txt')
@bp.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(current_app.static_folder, request.path[1:])

