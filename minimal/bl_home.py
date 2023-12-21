import socket
from io import BytesIO
import flask
from flask import (
    Blueprint, render_template, request, send_from_directory, flash, url_for, Flask, current_app, session
)
from flask_socketio import join_room
from . import socketio
from .layoutUtils import *
from .auth import *
import os
import json
import urllib.parse
from minimal.s3 import GetConnection
import logging
from botocore.exceptions import ClientError
from confluent_kafka import Producer

kafka_producer = None
bp = Blueprint('bl_home', __name__)
b_first_time = True

@bp.route('/', methods=('GET', 'POST'))
@manage_cookie_policy

def index():
    global b_first_time

    results = {}
    error=0
    basedir = os.path.abspath(os.path.dirname('/data/cosi/'))
    #basedir = os.path.abspath('.')

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
                    results["bucketclaim"] = data["metadata"]["name"]
                    results["bucketname"] = data["spec"]["bucketName"]
                    results["endpoint"] = data["spec"]["secretS3"]["endpoint"]
                    results["accesskey"] = data["spec"]["secretS3"]["accessKeyID"]
                    results["secretkey"] = data["spec"]["secretS3"]["accessSecretKey"]
                    results["disablebuttons"] = "false"
    else:
        results["kafkaenabledswitch"] = current_app.config['KAFKA_SWITCH_CHECK_CHECKED']
        results["kafkabroker"] = current_app.config['KAFKA_BROKER']
        results["kafkatopic"] = current_app.config['KAFKA_TOPIC']
        if current_app.config['KAFKA_SWITCH_CHECK_CHECKED'] == "true":
            results["disablekafkabuttons"] = "false"

        results["objectenabledswitch"] = current_app.config['S3_METADATA_SWITCH_CHECK_CHECKED']
        results["objectendpoint"] = current_app.config['S3_ENDPOINT']
        results["objectaccesskey"] = current_app.config['S3_ACCESS_KEY']
        results["objectsecretkey"] = current_app.config['S3_SECRET_KEY']
        results["objectbucket"] = current_app.config['S3_BUCKET']
        if current_app.config['S3_METADATA_SWITCH_CHECK_CHECKED'] == "true":
            results["disableobjectbuttons"] = "false"

        if b_first_time:
            b_first_time = False
            # Initialize Kafka if configured on first get
            if current_app.config['KAFKA_SWITCH_CHECK_CHECKED']:
                initialize_kafka(current_app)


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

        # A little hack to alter the endpoint
        if endpoint.find("https://") != -1:
            endpoint = endpoint.replace("https://", "http://")
            endpoint = endpoint.replace("443", "80")

        # Enable only for testing against ECS Test Driver
        #bucketname = ''
        #endpoint = 'https://object.ecstestdrive.com'
        #accesskeyid = ''
        #secretkey = ''

        # Create boto3 s3client
        s3 = GetConnection.getConnection(endpoint, False, accesskeyid, secretkey)

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

            # A little hack to alter the endpoint
            if endpoint.find("https://") != -1:
                endpoint = endpoint.replace("https://", "http://")
                endpoint = endpoint.replace("443", "80")

            # Enable only for testing against ECS Test Driver
            #bucketname = ''
            #endpoint = 'https://object.ecstestdrive.com'
            #accesskeyid = ''
            #secretkey = ''

            objectkey = form_file_data.filename
            # Create boto3 s3client
            s3 = GetConnection.getConnection(endpoint, False, accesskeyid, secretkey)

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

            # A little hack to alter the endpoint
            if endpoint.find("https://") != -1:
                endpoint = endpoint.replace("https://", "http://")
                endpoint = endpoint.replace("443", "80")

            # Enable only for testing against ECS Test Driver
            #bucketname = ''
            #endpoint = 'https://object.ecstestdrive.com'
            #accesskeyid = ''
            #secretkey = ''

            # Create boto3 s3client
            s3 = GetConnection.getConnection(endpoint, False, accesskeyid, secretkey)

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


def delivery_callback(err, msg):
    if err:
        print('ERROR: Message failed delivery: {}'.format(err))
    else:
        print("Produced event to topic {topic}: key = {key:12} value = {value:12}".format(
            topic=msg.topic(), key=msg.key().decode('utf-8'), value=msg.value().decode('utf-8')))


@bp.route('/webhook', methods=['POST'])
def webhook():
    global kafka_producer
    kafkaswitch = None
    kafkabroker = None
    kafkatopic = None

    if 'KAFKA_SWITCH_CHECK_CHECKED' in flask.current_app.config:
        kafkaswitch = flask.current_app.config['KAFKA_SWITCH_CHECK_CHECKED']
    if 'KAFKA_BROKER' in flask.current_app.config:
        kafkabroker = flask.current_app.config['KAFKA_BROKER']
    if 'KAFKA_TOPIC' in flask.current_app.config:
        kafkatopic = flask.current_app.config['KAFKA_TOPIC']

    if 'S3_METADATA_SWITCH_CHECK_CHECKED' in flask.current_app.config:
        s3metadataswitch = flask.current_app.config['S3_METADATA_SWITCH_CHECK_CHECKED']
    if 'S3_ENDPOINT' in flask.current_app.config:
        s3endpoint = flask.current_app.config['S3_ENDPOINT']
    if 'S3_ACCESS_KEY' in flask.current_app.config:
        s3accesskey = flask.current_app.config['S3_ACCESS_KEY']
    if 'S3_SECRET_KEY' in flask.current_app.config:
        s3secretkey = flask.current_app.config['S3_SECRET_KEY']

    if request.method == 'POST':
        # Get Bucket Event Data
        event_data = json.loads(request.data)

        # Extract the bucket and object key from the json event data
        event_bucket = event_data['Records'][0]['s3']['bucket']['name']
        event_object_key = event_data['Records'][0]['s3']['object']['key']

        # If we're configured to grab the object metadata then do so
        if s3metadataswitch == "True":

            # A little hack to alter the endpoint to always use http
            if s3endpoint.find("https://") != -1:
                s3endpoint = s3endpoint.replace("https://", "http://")
                s3endpoint = s3endpoint.replace("443", "80")

            # Create boto3 s3client
            s3 = GetConnection.getConnection(s3endpoint, False, s3accesskey, s3secretkey)

            # Get the object metadata
            object_metadata = s3.head_object(Bucket=event_bucket, Key=event_object_key)

            # Add the metadata to the event data
            event_data['metadata'] = object_metadata['ResponseMetadata']['HTTPHeaders']



        # Send the event data to the UI via socketio
        roomid = current_app.config['uid']
        send_message(event='msg', namespace='/collectHooks', room=roomid, message=event_data)

        # Send the event data to Kafka if enabled
        if kafkaswitch == "True":

            # Send the event data to Kafka
            kafka_producer.produce(kafkatopic, key="abc", value=json.dumps(event_data).encode('utf-8'), callback=delivery_callback)
            eventsprocessed = kafka_producer.poll(10000)
            kafka_producer.flush()

            send_message(event='kafkamsg', namespace='/collectHooks', room=roomid, message="Bucket Event Sent to Kafka Topic: " + kafkatopic)

        return "Success"

    return "Failure"
@bp.route('/configuration', methods=['POST'])
def configuration():
    updated_config = {}
    results = {}

    if request.method == 'POST':
        # Grab form data
        form_data = request.form

        # Retrieve current text area value and kafka values
        kafkaSwitch = form_data['kafkaSwitch']
        kafkaBroker = form_data['kafkaBroker']
        kafkaTopic = form_data['kafkaTopic']

        objectSwitch = form_data['objectSwitch']
        objectEndpoint = form_data['objectEndpoint']
        objectAccessKey = form_data['objectAccessKey']
        objectSecretKey = form_data['objectSecretKey']
        objectBucket = form_data['objectBucket']

        # Update the configuration dictionary
        updated_config['KAFKA_SWITCH_CHECK_CHECKED'] = kafkaSwitch
        updated_config['KAFKA_BROKER'] = kafkaBroker
        updated_config['KAFKA_TOPIC'] = kafkaTopic
        updated_config['S3_METADATA_SWITCH_CHECK_CHECKED'] = objectSwitch
        updated_config['S3_ENDPOINT'] = objectEndpoint
        updated_config['S3_ACCESS_KEY'] = objectAccessKey
        updated_config['S3_SECRET_KEY'] = objectSecretKey
        updated_config['S3_BUCKET'] = objectBucket

        roomid = current_app.config['uid']

        # Update the configuration file
        current_app.config.update(updated_config)

        # Attempt to initialize Kafka
        if kafkaSwitch == "True":
            initialize_kafka(current_app)
            send_message(event='kafkamsg', namespace='/collectHooks', room=roomid, message="Kafka Enabled")
        else:
            send_message(event='kafkamsg', namespace='/collectHooks', room=roomid, message="Kafka Disabled")

        return "Success"


# MANAGE sitemap and robots calls
# These files are usually in root, but for Flask projects must
# be in the static folder
@bp.route('/robots.txt')
@bp.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(current_app.static_folder, request.path[1:])


# Sending Message through the websocket
def send_message(event, namespace, room, message):
    # print("Message = ", message)
    current_app.extensions['socketio'].emit(event, message, namespace=namespace, room=room)


# Execute on connecting
@socketio.on('connect', namespace='/collectHooks')
def socket_connect():
    # Display message upon connecting to the namespace
    print('Client Connected To NameSpace /collectHooks - ', request.sid)


# Execute on disconnecting
@socketio.on('disconnect', namespace='/collectHooks')
def socket_connect():
    # Display message upon disconnecting from the namespace
    print('Client disconnected From NameSpace /collectHooks - ', request.sid)


# Execute upon joining a specific room
@socketio.on('join_room', namespace='/collectHooks')
def on_room():
    if current_app.config['uid']:
        room = str(current_app.config['uid'])
        # Display message upon joining a room specific to the session previously stored.
        print(f"Socket joining room {room}")
        join_room(room)


# Execute upon encountering any error related to the websocket
@socketio.on_error_default
def error_handler(e):
    # Display message on error.
    print(f"socket error: {e}, {str(request.event)}")


def initialize_kafka(app):

    global kafka_producer

    if kafka_producer is None:
        # Create config dict
        kafkaconfig = dict()
        kafkaconfig['bootstrap.servers'] = current_app.config['KAFKA_BROKER']
        kafkaconfig['client.id'] = socket.gethostname()
        kafkaconfig['auto.offset.reset'] = current_app.config['KAFKA_AUTO_RESET']

        # Create producer
        kafka_producer = Producer(kafkaconfig)

    print("initialized_kafka!")


