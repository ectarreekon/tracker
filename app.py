import os
from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
import pytz
import urllib.parse

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB Atlas Configuration with improved connection handling
def get_database():
    """
    Establish and return a MongoDB database connection
    """
    try:
        # Parse connection string
        connection_string = os.getenv("MONGODB_CONNECTION_STRING")
        
        if not connection_string:
            raise ValueError("MongoDB connection string is not set in .env file")
        
        # Create a MongoClient
        client = MongoClient(connection_string)
        
        # Extract database name from connection string
        # Typical format: mongodb+srv://username:password@cluster.mongodb.net/database_name
        url_parts = connection_string.split('/')
        database_name = url_parts[-1].split('?')[0] if len(url_parts) > 3 else 'test'
        
        # Get the database
        db = client[database_name]
        
        print(f"Successfully connected to database: {database_name}")
        return db
    
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None

# Initialize database
db = get_database()

# Check if database connection was successful
if db is None:
    raise Exception("Failed to connect to MongoDB. Please check your connection string.")

# Get locations collection
locations_collection = db.locations

@app.route('/')
def index():
    """Render the main PWA page"""
    return render_template('index.html')

@app.route('/save-location', methods=['POST'])
def save_location():
    """
    Endpoint to save location data to MongoDB
    Expects JSON with latitude, longitude
    """
    data = request.get_json()
    
    location_entry = {
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude'),
        'timestamp': datetime.now(pytz.UTC),
        'device_id': data.get('device_id', 'unknown')
    }
    
    try:
        result = locations_collection.insert_one(location_entry)
        return jsonify({
            'status': 'success', 
            'message': 'Location saved',
            'inserted_id': str(result.inserted_id)
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'message': str(e)
        }), 500

@app.route('/get-locations', methods=['GET'])
def get_locations():
    """
    Retrieve recent location entries
    Supports optional filtering by device_id
    """
    device_id = request.args.get('device_id', 'unknown')
    locations = list(locations_collection.find({
        'device_id': device_id
    }).sort('timestamp', -1).limit(50))
    
    # Convert ObjectId to string for JSON serialization
    for location in locations:
        location['_id'] = str(location['_id'])
        location['timestamp'] = location['timestamp'].isoformat()
    
    return jsonify(locations), 200

# Service Worker and Manifest routes
@app.route('/service-worker.js')
def service_worker():
    return app.send_static_file('service-worker.js')

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)