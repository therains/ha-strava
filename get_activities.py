from flask import Flask, request, jsonify, send_file
from stravalib.client import Client
import threading
import webbrowser
from datetime import datetime
import time
import polyline
import io
import matplotlib.pyplot as plt
import matplotlib

# Set the matplotlib backend to 'Agg'
matplotlib.use('Agg')

app = Flask(__name__)
client = Client()

# Use your actual client_id and client_secret
client_id = 'SUPERSECRETCLIENTID'
client_secret = 'SUPERSECRETCLIENTSECRET'
port = 8282
url = f'http://localhost:{port}/authorized'

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
    print(f"For {athlete.id}, I now have an access token {access_token}")
    print("Token expires at: " + expires_at_readable)
    
    return "Authorization Successful!"

@app.route("/activity_data", methods=["GET"])
def activity_data():
    ensure_strava_access()

    # Fetch recent activities
    activities = client.get_activities()
    activity_data = []
    for activity in activities:
        # Fetch the detailed activity to get segment efforts
        detailed_activity = client.get_activity(activity.id)
        
        distance_miles = detailed_activity.distance.magnitude * 0.000621371 if detailed_activity.distance else None
        moving_time_minutes = detailed_activity.moving_time.total_seconds() / 60 if detailed_activity.moving_time else None
        avg_speed_mph = detailed_activity.average_speed.magnitude * 2.23694 if detailed_activity.average_speed else None
        total_elevation_feet = detailed_activity.total_elevation_gain.magnitude * 3.28084 if detailed_activity.total_elevation_gain else None
        max_speed_mph = detailed_activity.max_speed.magnitude * 2.23694 if detailed_activity.max_speed else None

        segment_efforts = []
        if detailed_activity.segment_efforts:
            for effort in detailed_activity.segment_efforts:
                effort_achievements = []
                if effort.achievements:
                    for achievement in effort.achievements:
                        effort_achievements.append({
                            "type": achievement.type,
                            "rank": achievement.rank
                        })

                segment_efforts.append({
                    "id": getattr(effort, 'id', None),
                    "name": getattr(effort.segment, 'name', None),
                    "distance": effort.distance.magnitude if effort.distance else None,
                    "moving_time": effort.moving_time.total_seconds() if effort.moving_time else None,
                    "elapsed_time": effort.elapsed_time.total_seconds() if effort.elapsed_time else None,
                    "start_date": effort.start_date.isoformat() if effort.start_date else None,
                    "start_date_local": effort.start_date_local.isoformat() if effort.start_date_local else None,
                    "pr_rank": getattr(effort, 'pr_rank', None),
                    "achievements": effort_achievements
                })

        activity_dict = {
            "id": getattr(detailed_activity, 'id', None),
            "resource_state": getattr(detailed_activity, 'resource_state', None),
            "external_id": getattr(detailed_activity, 'external_id', None),
            "upload_id": getattr(detailed_activity, 'upload_id', None),
            "athlete": {
                "id": getattr(detailed_activity.athlete, 'id', None),
                "resource_state": getattr(detailed_activity.athlete, 'resource_state', None)
            },
            "name": detailed_activity.name,
            "distance": round(distance_miles, 2) if distance_miles else None,
            "moving_time": round(moving_time_minutes, 2) if moving_time_minutes else None,
            "elapsed_time": getattr(detailed_activity, 'elapsed_time', None).total_seconds() if getattr(detailed_activity, 'elapsed_time', None) else None,
            "total_elevation_gain": round(total_elevation_feet, 2) if total_elevation_feet else None,
            "type": detailed_activity.type,
            "sport_type": getattr(detailed_activity, 'sport_type', None),
            "start_date": detailed_activity.start_date.isoformat() if detailed_activity.start_date else None,
            "start_date_local": detailed_activity.start_date_local.isoformat() if detailed_activity.start_date_local else None,
            "timezone": str(getattr(detailed_activity, 'timezone', None)),
            "utc_offset": getattr(detailed_activity, 'utc_offset', None),
            "achievement_count": getattr(detailed_activity, 'achievement_count', None),
            "kudos_count": getattr(detailed_activity, 'kudos_count', None),
            "comment_count": getattr(detailed_activity, 'comment_count', None),
            "athlete_count": getattr(detailed_activity, 'athlete_count', None),
            "photo_count": getattr(detailed_activity, 'photo_count', None),
            "map": {
                "id": getattr(detailed_activity.map, 'id', None),
                "polyline": getattr(detailed_activity.map, 'summary_polyline', None),
                "resource_state": getattr(detailed_activity.map, 'resource_state', None)
            },
            "trainer": getattr(detailed_activity, 'trainer', None),
            "commute": getattr(detailed_activity, 'commute', None),
            "manual": detailed_activity.manual,
            "private": detailed_activity.private,
            "flagged": getattr(detailed_activity, 'flagged', None),
            "gear_id": getattr(detailed_activity, 'gear_id', None),
            "from_accepted_tag": getattr(detailed_activity, 'from_accepted_tag', None),
            "average_speed": round(avg_speed_mph, 2) if avg_speed_mph else None,
            "max_speed": round(max_speed_mph, 2) if max_speed_mph else None,
            "device_watts": getattr(detailed_activity, 'device_watts', None),
            "has_heartrate": getattr(detailed_activity, 'has_heartrate', None),
            "average_heartrate": getattr(detailed_activity, 'average_heartrate', None),
            "max_heartrate": getattr(detailed_activity, 'max_heartrate', None),
            "pr_count": getattr(detailed_activity, 'pr_count', None),
            "total_photo_count": getattr(detailed_activity, 'total_photo_count', None),
            "has_kudoed": getattr(detailed_activity, 'has_kudoed', None),
            "workout_type": getattr(detailed_activity, 'workout_type', None),
            "description": getattr(detailed_activity, 'description', None),
            "calories": getattr(detailed_activity, 'calories', None),
            "segment_efforts": segment_efforts
        }
        activity_data.append(activity_dict)

    return jsonify(activity_data)

@app.route("/personal_bests", methods=["GET"])
def personal_bests():
    ensure_strava_access()

    # Fetch activities and compute personal bests
    activities = client.get_activities(limit=100)
    best_5k = None
    best_10k = None
    best_half_marathon = None

    for activity in activities:
        detailed_activity = client.get_activity(activity.id)
        if detailed_activity.type != 'Run':
            continue

        distance = detailed_activity.distance.magnitude  # in meters
        time_seconds = detailed_activity.moving_time.total_seconds()  # in seconds

        if 5000 <= distance <= 5100:
            if not best_5k or time_seconds < best_5k:
                best_5k = time_seconds

        if 10000 <= distance <= 10200:
            if not best_10k or time_seconds < best_10k:
                best_10k = time_seconds

        if 21097 <= distance <= 21150:
            if not best_half_marathon or time_seconds < best_half_marathon:
                best_half_marathon = time_seconds

    personal_bests = {
        "5k": round(best_5k / 60, 2) if best_5k else None,
        "10k": round(best_10k / 60, 2) if best_10k else None,
        "half_marathon": round(best_half_marathon / 60, 2) if best_half_marathon else None
    }

    return jsonify(personal_bests)

@app.route("/map", methods=["GET"])
def map_route():
    ensure_strava_access()
    
    activity_name = request.args.get('name')
    if not activity_name:
        return "Activity name not provided", 400

    # Fetch activities and find the one with the given name
    activities = client.get_activities(limit=100)
    activity = next((act for act in activities if act.name == activity_name), None)

    if not activity:
        return "Activity not found", 404

    if not activity.map.summary_polyline:
        return "No polyline available for this activity", 404

    # Decode the polyline
    coordinates = polyline.decode(activity.map.summary_polyline)

    # Plot the polyline
    fig, ax = plt.subplots()
    lats, lons = zip(*coordinates)
    ax.plot(lons, lats, marker=None)
    ax.set_title(f'Activity: {activity_name}')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')

    # Save the plot to a BytesIO object
    img_bytes = io.BytesIO()
    plt.savefig(img_bytes, format='png')
    img_bytes.seek(0)

    return send_file(img_bytes, mimetype='image/png', as_attachment=True, download_name=f'{activity_name}_map.png')

def open_auth_url():
    authorize_url = client.authorization_url(client_id=client_id, redirect_uri=url)
    webbrowser.open(authorize_url)

def ensure_strava_access():
    # Check if token is close to expiry (within 1 minute)
    if time.time() > client.token_expires_at - 60:
        refresh_response = client.refresh_access_token(client_id=client_id, client_secret=client_secret, refresh_token=client.refresh_token)
        
        client.access_token = refresh_response['access_token']
        client.refresh_token = refresh_response['refresh_token']
        client.token_expires_at = refresh_response['expires_at']

# Start the Flask server in a new thread
flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port))
flask_thread.start()

# Open the Strava authorization page in the user's web browser
open_auth_url()
