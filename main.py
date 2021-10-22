import json
import os
import shutil
import time
import pickle
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from stravalib.client import Client
import enum
import xml.etree.cElementTree as ET


with open('configTest.json') as json_file:
    data = json.load(json_file)
CLIENT_ID = data['CLIENT_ID']
CLIENT_SECRET = data['CLIENT_SECRET']
REDIRECT_URL = 'http://localhost:8000/authorized'

app = FastAPI()
client = Client()

def save_object(obj, filename):
    with open(filename, 'wb') as output:  # Overwrites any existing file.
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

def load_object(filename):
    with open(filename, 'rb') as input:
        loaded_object = pickle.load(input)
        return loaded_object


def check_token():
    if time.time() > client.token_expires_at:
        refresh_response = client.refresh_access_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, refresh_token=client.refresh_token)
        access_token = refresh_response['access_token']
        refresh_token = refresh_response['refresh_token']
        expires_at = refresh_response['expires_at']
        client.access_token = access_token
        client.refresh_token = refresh_token
        client.token_expires_at = expires_at

@app.get("/")
def read_root():
    authorize_url = client.authorization_url(client_id=CLIENT_ID, redirect_uri=REDIRECT_URL)
    return RedirectResponse(authorize_url)


def get_code2(state=None, code=None, scope=None):
    path='./gpx/'
    try:
        shutil.rmtree(path, ignore_errors=True, onerror=None)
        os.makedirs(path, exist_ok=False)
    except OSError:
        print("Creation of the directory %s failed" % path)
    else:
        print("Successfully created the directory %s " % path)

    for activity in client.get_activities(limit=5):
        print(activity.type)
        if activity.type != "Ride":
            pass

        s = client.get_activity_streams(activity.id, types=['latlng','time','altitude'])
        data = s['latlng'].data

        root = ET.Element("gpx")
        meta = ET.SubElement(root, "metadata")
        trk = ET.SubElement(root,'trk')
        trkseg = ET.SubElement(trk,'trkseg')

        ET.SubElement(meta, "field1", name="blah").text = "some value1"
        ET.SubElement(meta, "field2", name="asdfasd").text = "some vlaue2"

        ET.SubElement(trk,'name').text = "Example GPX Document"

        for i,k in enumerate(data):
            trkpt = ET.SubElement(trkseg,'trkpt' , lat=str(data[i][0]),lon=str(data[i][1]))
            ele = ET.SubElement(trkpt,'ele').text = str(s['altitude'].data[i])
            time = ET.SubElement(trkpt, 'time').text = str(s['time'].data[i])
        tree = ET.ElementTree(root)
        tree.write(path+str(activity.id)+".gpx")
    shutil.rmtree('./gpx-archive.zip', ignore_errors=True, onerror=None)
    shutil.make_archive('gpx-archive', 'zip', path)



@app.get("/authorized/")
def get_code(state=None, code=None, scope=None):
    token_response = client.exchange_code_for_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, code=code)
    access_token = token_response['access_token']
    refresh_token = token_response['refresh_token']
    expires_at = token_response['expires_at']
    client.access_token = access_token
    client.refresh_token = refresh_token
    client.token_expires_at = expires_at
    save_object(client, 'client.pkl')
    return {"state": state, "code": code, "scope": scope}

if __name__ == "__main__":
    try:
        client = load_object('client.pkl')
        check_token()
        athlete = client.get_athlete()
        print("For {id}, I now have an access token {token}".format(id=athlete.id, token=client.access_token))
        get_code2()
        # To upload an activity
        # client.upload_activity(activity_file, data_type, name=None, description=None, activity_type=None, private=None, external_id=None)
    except FileNotFoundError:
        print("No access token stored yet, visit http://localhost:8000/ to get it")
        print("After visiting that url, a pickle file is stored, run this file again")
