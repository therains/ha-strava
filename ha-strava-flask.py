from flask import Flask, request, jsonify
from stravalib.client import Client
import threading
import webbrowser
from datetime import datetime
import json

app = Flask(__name__)
client = Client()

# Use your actual client_id and client_secret
client_id = ''
client_secret = ''
port = 8282
url = 'http://localhost:{}/authorized'.format(port)

@app.route("/authorized")
def authorized():
    code = request.args.get('code')
    print('Strava provided the following code: ' + code)
    token_response = client.exchange_code_for_token(client_id=client_id, client_secret=client_secret, code=code)
    
    access_token = token_response['access_token']
    refresh_token = token_response['refresh_token']
    expires_at = token_response['expires_at']
    expires_at_readable = datetime.fromtimestamp(expires_at).strftime('%Y-%m-%d %H:%M:%S')

    client.access_token = access_token
    client.refresh_token = refresh_token
    client.token_expires_at = expires_at

    athlete = client.get_athlete()
    print("For {id}, I now have an access token {token}".format(id=athlete.id, token=access_token))
    print("Token expires at: {}".format(expires_at_readable))

    # Fetch recent activities
    activities = client.get_activities(limit=10)
    activity_data = []
    for activity in activities:
        # Convert the distance from meters to miles
        distance_miles = activity.distance.num * 0.000621371
        # Convert the moving time from seconds to minutes
        moving_time_minutes = activity.moving_time.seconds / 60
        # Convert the average speed from m/s to mph
        avg_speed_mph = activity.average_speed.num * 2.23694
        # Convert the total elevation gain from meters to feet
        total_elevation_feet = activity.total_elevation_gain.num * 3.28084

        activity_dict = {
            "name": activity.name,
            "type": activity.type,
            "distance": round(distance_miles, 2),
            "moving_time": round(moving_time_minutes, 2),
            "average_speed": round(avg_speed_mph, 2),
            "total_elevation_gain": round(total_elevation_feet, 2)
        }
        activity_data.append(activity_dict)

    return jsonify(activity_data)

# open web browser auth to strava
def open_auth_url():
    authorize_url = client.authorization_url(client_id=client_id, redirect_uri=url)
    print(authorize_url)
    webbrowser.open(authorize_url)

# Start the Flask server 
flask_thread = threading.Thread(target=lambda: app.run(port=port))
flask_thread.start()

# Open the Strava authorization page in the user's web browser
open_auth_url()
