from flask import Flask, request, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId
import openai
from huggingface_hub import InferenceClient
import json
import ssl

from flask_socketio import SocketIO, join_room
import warnings
from urllib3.exceptions import NotOpenSSLWarning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

from random import randint
from email.mime.text import MIMEText
import smtplib
from pymongo import MongoClient
from datetime import datetime, timedelta

import six
import sys
if sys.version_info >= (3, 12, 0):
    sys.modules['kafka.vendor.six.moves'] = six.moves

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from flask_socketio import SocketIO
import threading
import json
import os


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB connection
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(mongo_uri)
#mongo_uri = "mongodb+srv://Kingsarthucodes:starduckWRMS1$@cluster-filia.qbyj9.mongodb.net/"
#client = MongoClient(mongo_uri, server_api=ServerApi('1'))


# Database and collections
db = client["filia_database"]

verification_collection = db["email_verifications"]
students_collection = db["students"]
neighbors_collection = db["neighbors"]  # Add a collection for neighbors
# db = client['job_db']  # Database name
jobs_collection = db['jobs']  # Collection name
students_services_collection = db["student_services"]
neighbors_job_collection = db["neighbor_jobs"]
neighbors_requested_services_collection = db["neighbor_req_services"]
students_requested_services_collection = db['students_req_services']


# Test MongoDB connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# Helper to serialize MongoDB documents
def serialize_document(doc):
    doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
    return doc

# Get a list of schools (GET)
@app.route('/api/schools', methods=['GET'])
def get_schools():
    try:
        # Hardcoded list of schools
        schools = [
            "UC Berkeley",
            "UC Merced",
            "Stanford University",
            "MIT",
            "Harvard University",
            "UCLA",
            "UC San Diego"
        ]
        print("Returning list of schools:", schools)
        return jsonify(schools), 200
    except Exception as e:
        print(f"Error fetching schools: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500


# Get a list of services (GET)
@app.route('/api/services', methods=['GET'])
def get_services():
    try:
        # Hardcoded list of services
        services = [
            "Tutoring",
            "Cleaning",
            "Dogwalking",
            "Gardening",
            "Babysitting",
            "Personal Training"
        ]
        print("Returning list of services:", services)
        return jsonify(services), 200
    except Exception as e:
        print(f"Error fetching services: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500



# Create a student record (POST)
@app.route('/api/students', methods=['POST'])
def create_student():
    try:
        data = request.get_json()
        email = data.get("email")
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Check if the email has been verified
        verification_entry = verification_collection.find_one({"email": email})
        if not verification_entry:
            return jsonify({"error": "Email not verified."}), 400

        # Existing logic to create a student record
        required_fields = ['studyField', 'services', 'school', 'travelDistance']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        student = {
            "email": email,
            "studyField": data['studyField'],
            "services": data['services'],
            "school": data['school'],
            "travelDistance": data['travelDistance'],
            "idImage": data.get('idImage', None),
        }

        result = students_collection.insert_one(student)
        student["_id"] = str(result.inserted_id)

        # Clean up verification entry after registration
        verification_collection.delete_one({"email": email})

        return jsonify(student), 201

    except Exception as e:
        print(f"Error during student creation: {e}")
        return jsonify({'error': str(e)}), 500

# Get all student records (GET)
@app.route('/api/students', methods=['GET'])
def get_students():
    try:
        students = list(students_collection.find())
        students = [serialize_document(student) for student in students]
        return jsonify(students), 200
    except Exception as e:
        print(f"Error fetching students: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# Get a specific student record (GET)
@app.route('/api/students/<string:student_id>', methods=['GET'])
def get_student(student_id):
    try:
        student = students_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        return jsonify(serialize_document(student)), 200
    except Exception as e:
        print(f"Error fetching student: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# Search for a student by email (GET)
@app.route('/api/students/search', methods=['GET'])
def search_student_by_email():
    try:
        # Get the email from query parameters
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        print("Searching for student with email:", email)

        # Find the student by email
        student = students_collection.find_one({"email": email})
        if not student:
            return jsonify({'error': 'Student not found'}), 404

        print("Found student:", student)

        return jsonify(serialize_document(student)), 200

    except Exception as e:
        print(f"Error searching for student: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# ----------------------------------------
# NEIGHBOR APIs
# ----------------------------------------

# Create a neighbor record (POST)
@app.route('/api/neighbors', methods=['POST'])
def create_neighbor():
    try:
        data = request.get_json()
        print("Received Data (Neighbor):", data)

        # Validate required fields
        required_fields = ['name', 'email','phoneNbr']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        # Prepare neighbor document
        neighbor = {
            "name": data['name'],
            "email": data['email'],
            "address": data['address'],
            "phoneNbr": data['phoneNbr'],
            "schoolofpreference" : data['school']
        }

        print("Inserting Neighbor into MongoDB:", neighbor)
        result = neighbors_collection.insert_one(neighbor)
        neighbor["_id"] = str(result.inserted_id)  # Convert ObjectId to string for response
        print("Inserted Neighbor ID:", neighbor["_id"])

        # Always return a valid JSON object
        return jsonify(neighbor), 201

    except Exception as e:
        print(f"Error during neighbor creation: {e}")
        return jsonify({'error': str(e)}), 500


# Get all neighbor records (GET)
@app.route('/api/neighbors', methods=['GET'])
def get_neighbors():
    try:
        neighbors = list(neighbors_collection.find())
        neighbors = [serialize_document(neighbor) for neighbor in neighbors]
        return jsonify(neighbors), 200
    except Exception as e:
        print(f"Error fetching neighbors: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# Get a specific neighbor record (GET)
@app.route('/api/neighbors/<string:neighbor_id>', methods=['GET'])
def get_neighbor(neighbor_id):
    try:
        neighbor = neighbors_collection.find_one({"_id": ObjectId(neighbor_id)})
        if not neighbor:
            return jsonify({'error': 'Neighbor not found'}), 404
        return jsonify(serialize_document(neighbor)), 200
    except Exception as e:
        print(f"Error fetching neighbor: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

# Search for a neighbor by email (GET)
@app.route('/api/neighbors/search', methods=['GET'])
def search_neighbor_by_email():
    try:
        # Get the email from query parameters
        email = request.args.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        print("Searching for Neighbor with email:", email)

        # Find the student by email
        neighbor = neighbors_collection.find_one({"email": email})
        if not neighbor:
            return jsonify({'error': 'Neighbor not found'}), 404

        print("Found student:", neighbor)

        return jsonify(serialize_document(neighbor)), 200

    except Exception as e:
        print(f"Error searching for Neighbor: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500
    
@app.route('/api/students/<string:student_id>', methods=['PUT'])
def update_student(student_id):
    try:
        data = request.get_json()
        updated_fields = {
            "email": data.get("email"),
            "idImage": data.get("idImage"),
            "school": data.get("school"),
            "services": data.get("services"),
            "studyField": data.get("studyField"),
            "travelDistance": data.get("travelDistance"),
        }
        # Remove None values from the update payload
        updated_fields = {k: v for k, v in updated_fields.items() if v is not None}
        
        result = students_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": updated_fields}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Student not found"}), 404

        return jsonify({"message": "Student updated successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------------------
# JOB APIs
# ----------------------------------------

# Create a job posting (POST)


# Job statuses
JOB_STATUSES = ["New", "Active", "Inactive", "Cancelled", "In Progress"]

#@app.route('/api/jobs', methods=['POST'])
def create_job():
    """
    API to create a new job
    """
    try:
        data = request.get_json()
        print("Received Data (Job):", data)

        # Validate required fields
        required_fields = ['email', 'job_title', 'job_description', 'hours', 'price', 'services']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        # Prepare job document
        job = {
            "email": data['email'],
            "job_title": data['job_title'],
            "job_description": data['job_description'],
            "hours": data['hours'],
            "price": data['price'],
            "services": data['services'],  # List of services
            "status": "New",  # Default status
        }

        print("Inserting Job into MongoDB:", job)
        result = jobs_collection.insert_one(job)
        job["_id"] = str(result.inserted_id)
        print("Inserted Job ID:", job["_id"])

        return jsonify(job), 201

    except Exception as e:
        print(f"Error during job creation: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/jobs/<job_id>', methods=['PUT'])
def update_job_status(job_id):
    """
    API to update the status of a job
    """
    try:
        data = request.get_json()
        print("Received Data (Update Status):", data)

        # Validate required fields
        if 'status' not in data or data['status'] not in JOB_STATUSES:
            return jsonify({'error': f'Invalid status. Must be one of {JOB_STATUSES}'}), 400

        # Find and update the job
        updated_job = jobs_collection.find_one_and_update(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": data['status']}},
            return_document=True
        )

        if not updated_job:
            return jsonify({'error': 'Job not found'}), 404

        # Convert ObjectId to string for JSON serialization
        updated_job["_id"] = str(updated_job["_id"])

        return jsonify({"message": "Job status updated successfully", "job": updated_job}), 200

    except Exception as e:
        print(f"Error during job update: {e}")
        return jsonify({'error': str(e)}), 500
# Get all job postings (GET)
##@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    try:
        jobs = list(jobs_collection.find())
        jobs = [serialize_document(job) for job in jobs]
        return jsonify(jobs), 200
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500
    


# Get a specific job posting (GET)
@app.route('/api/jobs/<string:job_id>', methods=['GET'])
def get_job(job_id):
    try:
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(serialize_document(job)), 200
    except Exception as e:
        print(f"Error fetching job: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500



#inference = InferenceApi(repo_id=model_id, token=HF_API_KEY)
import requests
HF_API_KEY = "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"  # Replace with your API key
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-2-7b-chat-hf"
headers = {"Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json",}

def hf_query(payload):

    print("In hf ",payload)

    categories = {'cleaning', 'dogwalking', 'gardening', 'babysitting', 'personal training'}

    prompt = (
        f"[INST] <<SYS>>\n"
        f"Classify the following job category for this text: '{payload}': tutoring, "
        f"{categories} "
        f"Then generate an appropriate short simple title. Return the category or multiple categories if there are more than 1 "
        f"and title in JSON format like this: "
        f"{{'category': 'tutoring', 'title': 'Math Tutoring Services'}}."
        f"<</SYS>>\n"
        f"Give me just the assistant response as a JSON \n"
        f"[/INST]"
    )

    # json_body = {
    #     "inputs": prompt,"parameters": {"max_new_tokens":256, "top_p":0.9, "temperature":0}
    #     }
    # data = json.dumps(json_body)
    # print("response ==> ", data)
    # response = requests.request("POST", HF_API_URL, headers=headers, data=data)

    messages = [{"role": "user", "content": prompt}]
    client = InferenceClient("meta-llama/Meta-Llama-3-8B-Instruct",token=HF_API_KEY)
    response = client.chat_completion(messages, max_tokens=100)
    print("response ======= ",response)
    print("response 0 ======= ",response.choices[0])
    print("response 1 ======= ",response.choices[0].message)
    

    # Parse JSON
    # parsed_data = json.loads(json_text)
    # category = parsed_data.get("category")
    # title = parsed_data.get("title")
    # print("Category:", category)
    # print("Title:", title)
    #print("returning ======> ", json.loads(response.content.decode("utf-8")))
    try:
        #print("returning ======> ", json.loads(response.choices[0].message.decode("utf-8")))
        return json.loads(response.choices[0].message.content)
    except:
        return response
@app.route('/api/neighbors/job', methods=['POST'])
def manage_job():
    """
    API to classify job details or save final job postings based on 'mode'.
    """
    try:
        data = request.json
        mode = data.get('mode', 'generate')  # Default to 'generate'
        email = data.get('email')

        # Validate email
        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Handle 'generate' mode
        if mode == 'generate':
            text = data.get('text')
            hours = data.get('hours')
            pay = data.get('pay')
            additional_details = data.get('additionalDetails', "No additional details provided.")

            # Validate required fields
            if not text:
                return jsonify({"error": "Text is required"}), 400

            try:
                hours = int(hours)
                pay = float(pay)
                if pay < 0:
                    raise ValueError("Pay must be positive.")
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid hours or pay provided."}), 400

            # Call HF API to classify job
            try:
                response = hf_query(text)
            except Exception as e:
                print(f"Error in hf_query: {e}")
                return jsonify({"error": "Failed to classify job details"}), 500

            if not response or "category" not in response or "title" not in response:
                return jsonify({"error": "Invalid response from classification API"}), 500

            # Parse categories and titles
            categories = response.get("category", [])
            title = response.get("title", "Default Title")
            if isinstance(categories, str):
                categories = [categories]

            # Prepare job entries
            job_entries = [
                {
                    "job_id": f"temp_{i}",  # Temporary ID
                    "title": f"{title}, {category.capitalize()}",
                    "category": category,
                }
                for i, category in enumerate(categories)
            ]

            return jsonify({
                "message": "Job details generated successfully",
                "jobs": job_entries
            }), 200

        # Handle 'post' mode
        elif mode == 'post':
            text = data.get('text')
            hours = data.get('hours')
            pay = data.get('pay')
            additional_details = data.get('additionalDetails', "No additional details provided.")
            title = data.get('title', "Untitled Job")
            category = data.get('category', "Uncategorized")

            # Validate required fields
            required_fields = ['text', 'hours', 'pay', 'title', 'category']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({"error": f"{field} is required"}), 400

            final_job = {
                "text": text,
                "hours": int(hours),
                "pay": float(pay),
                "additional_details": additional_details,
                "title": title,
                "category": category,
                "posted_by": "neighbor",
                "posted_by_email": email,
                "status": "unaccepted",
            }

            # Insert into MongoDB
            result = neighbors_job_collection.insert_one(final_job)
            final_job["_id"] = str(result.inserted_id)

            return jsonify({
                "message": "Job posted successfully",
                "job": final_job
            }), 201

        else:
            return jsonify({"error": "Invalid mode"}), 400

    except Exception as e:
        print(f"Error in manage_job: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500



# 1. STUDENT SERVICES (GET): Fetch student services for neighbors
@app.route('/api/students/services', methods=['GET'])
def get_student_services():
    """
    Fetch services posted by students for neighbors to view
    """
    try:
        services = list(students_services_collection.find({"posted_by": "student"}))
        # Ensure email is included in the serialized response
        services = [
            {
                **serialize_document(service),
                "email": service.get("email")  # Explicitly include email
            }
            for service in services
        ]
        return jsonify(services), 200
    except Exception as e:
        print(f"Error fetching student services: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500


# 2. CREATE STUDENT SERVICE (POST): Allow students to post services
@app.route('/api/students/services', methods=['POST'])
def create_student_service():
    """
    API for students to create services
    """
    try:
        data = request.get_json()
        print("Received Data (Service):", data)

        # Validate required fields
        required_fields = ['email', 'job_title', 'job_description', 'hours', 'price', 'services']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        # Prepare the service document
        job = {
            "posted_by": "student",
            "email": data['email'],
            "job_title": data['job_title'],
            "job_description": data['job_description'],
            "hours": data['hours'],
            "price": data['price'],
            "services": data['services'],
            "status": "New",
        }

        print("Inserting Service into MongoDB:", job)
        result = students_services_collection.insert_one(job)
        job["_id"] = str(result.inserted_id)
        print("Inserted Service ID:", job["_id"])

        return jsonify(job), 201

    except Exception as e:
        print(f"Error creating student service: {e}")
        return jsonify({'error': str(e)}), 500


# 3.1 NEIGHBOR JOBS (GET ALL): Fetch all neighbor jobs for students
@app.route('/api/jobs/neighbor', methods=['GET'])
def get_all_neighbor_jobs():
    """
    Fetch all jobs posted by neighbors for students to view.
    """
    try:
        jobs = list(neighbors_job_collection.find({"posted_by": "neighbor"}))  # Filter neighbor jobs
        print("Fetched Jobs:", jobs)  # Debugging
        jobs = [serialize_document(job) for job in jobs]  # Serialize for JSON response
        return jsonify(jobs), 200
    except Exception as e:
        print(f"Error fetching neighbor jobs: {e}")
        return jsonify({'error': 'An internal server error occurred.'}), 500

from bson.objectid import ObjectId  # Import ObjectId to handle MongoDB IDs

@app.route('/api/jobs/neighbor/<job_id>', methods=['GET'])
def get_neighbor_job_details(job_id):
    """
    Fetch details of a specific job posted by a neighbor.
    """
    try:
        # Validate the job_id
        if not ObjectId.is_valid(job_id):
            return jsonify({"error": "Invalid job ID"}), 400

        # Find the job by its ID
        job = neighbors_job_collection.find_one({"_id": ObjectId(job_id), "posted_by": "neighbor"})
        if not job:
            return jsonify({"error": "Job not found"}), 404

        # Serialize the job document for JSON response
        job = serialize_document(job)
        return jsonify(job), 200
    except Exception as e:
        print(f"Error fetching job details: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500


@app.route('/api/jobs/my_jobs', methods=['GET'])
def get_my_jobs():
    """
    Fetch all jobs posted by a specific neighbor.
    """
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Find jobs posted by this neighbor
        jobs = list(neighbors_job_collection.find({"posted_by_email": email}))
        if not jobs:
            return jsonify([]), 200

        # Serialize the job documents for JSON response
        jobs = []
        for job in neighbors_job_collection.find({"posted_by_email": email}):
            serialized_job = serialize_document(job)
            serialized_job["status"] = job.get("status", "New")  # Fallback to "New" if status is not available
            jobs.append(serialized_job)

        return jsonify(jobs), 200
    except Exception as e:
        print(f"Error fetching jobs for neighbor: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500



@app.route('/api/jobs/my_jobs_student', methods=['GET'])
def get_my_jobs_student():
    """
    Fetch jobs posted by a student, ensuring accurate status.
    """
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Fetch jobs posted by the student
        jobs = list(students_services_collection.find({"email": email}))

        for job in jobs:
            try:
                service_object_id = job["_id"]

                # Check for a request in the neighbors' collection
                neighbor_request = neighbors_requested_services_collection.find_one(
                    {"service_id": service_object_id}
                )

                # Check for accepted status in the students' services collection
                if job.get("status") == "accepted":
                    job["status"] = "accepted"
                elif neighbor_request:
                    job["status"] = "requested"  # Update to requested
                    job["requested_by"] = neighbor_request.get("requested_by", None)
                else:
                    job["status"] = "pending"  # Default fallback status
                    job["requested_by"] = None

            except Exception as e:
                print(f"Error updating job status for {job['_id']}: {e}")
                job["status"] = "pending"
                job["requested_by"] = None

        # Serialize jobs for JSON response
        jobs = [serialize_document(job) for job in jobs]
        return jsonify(jobs), 200

    except Exception as e:
        print(f"Error fetching jobs for student: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500




@app.route('/api/services/request', methods=['POST'])
def request_service():
    try:
        data = request.json
        print("Received Payload:", data)

        # Extract job details
        service_id = data.get("serviceId")
        neighbor_email = data.get("neighborEmail")
        service_details = data.get("serviceDetails")

        # Validate required fields
        if not service_id or not neighbor_email or not service_details:
            missing_fields = [field for field in ["Service ID", "Neighbor Email", "Service Details"]
                              if not data.get(field.lower().replace(" ", ""))]
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        if not ObjectId.is_valid(service_id):
            print(f"Invalid Service ID: {service_id}")
            return jsonify({"error": "Invalid Service ID"}), 400

        service_object_id = ObjectId(service_id)

        # Check if the service exists in students_services_collection
        student_job = students_services_collection.find_one({"_id": service_object_id})
        if not student_job:
            print(f"Job not found in students_services_collection for service_id: {service_id}")
            return jsonify({"error": f"Job not found for service_id: {service_id}"}), 404

        # Check if the request already exists
        existing_request = neighbors_requested_services_collection.find_one({
            "service_id": service_object_id,
            "requested_by": neighbor_email
        })
        if existing_request:
            print(f"Request already exists for service_id {service_id} by {neighbor_email}")
            return jsonify({"error": "You have already requested this service"}), 400

        # Insert the request into the neighbors_requested_services_collection
        request_entry = {
            "service_id": service_object_id,
            "service_details": {
                "jobTitle": service_details.get("jobTitle"),
                "jobDescription": service_details.get("jobDescription"),
                "hours": service_details.get("hours"),
                "price": service_details.get("price"),
                "services": service_details.get("services"),
                "postedBy": service_details.get("postedBy"),
            },
            "requested_by": neighbor_email,
            "status": "pending",
        }
        neighbors_requested_services_collection.insert_one(request_entry)

        # Update the status in students_services_collection
        update_result = students_services_collection.update_one(
            {"_id": service_object_id},
            {"$set": {"status": "requested"}}
        )

        if update_result.matched_count == 0:
            print(f"Warning: No matching job found in students_services_collection for service_id {service_id}")
            return jsonify({"error": f"Failed to update job status for service_id {service_id}"}), 500

        print(f"Job {service_id} status updated to 'requested'.")
        print("Inserted Request Entry:", request_entry)
        return jsonify({"message": "Service requested successfully"}), 201

    except Exception as e:
        print(f"Error requesting service: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500
@app.route('/api/jobs/accept_job', methods=['POST'])
def accept_job():
    """
    API for accepting a job, whether posted by a student or neighbor.
    """
    try:
        # Parse request data
        data = request.json
        job_id = data.get("jobId")
        actor_email = data.get("email")  # Email of the neighbor or student accepting the job

        # Validate input
        if not job_id or not actor_email:
            return jsonify({"error": "Job ID and email are required"}), 400

        if not ObjectId.is_valid(job_id):
            return jsonify({"error": "Invalid job ID"}), 400

        service_object_id = ObjectId(job_id)

        # Step 1: Check if the job exists in the students' services collection
        job_student = students_services_collection.find_one(
            {"_id": service_object_id, "status": "requested"}
        )
        if job_student:
            print(f"Job found in students_services_collection: {job_student}")

            # Update the job status to 'accepted' in the students' collection
            students_services_collection.update_one(
                {"_id": service_object_id},
                {"$set": {"status": "accepted", "accepted_by": actor_email}}
            )
            print(f"Job {job_id} updated to 'accepted' in students_services_collection.")

            # Synchronize the status in the neighbors' job collection
            neighbors_job_collection.update_one(
                {"_id": service_object_id},
                {"$set": {"status": "accepted", "accepted_by": actor_email}},
                upsert=True  # Use upsert to ensure the entry is created if it doesn't exist
            )
            print(f"Job {job_id} status synced to 'accepted' in neighbors_job_collection.")

            return jsonify({"message": "Job accepted successfully"}), 200

        # Step 2: Check if the job exists in the neighbors' job collection
        job_neighbor = neighbors_job_collection.find_one(
            {"_id": service_object_id, "status": "requested"}
        )
        if job_neighbor:
            print(f"Job found in neighbors_job_collection: {job_neighbor}")

            # Update the job status to 'accepted' in the neighbors' collection
            neighbors_job_collection.update_one(
                {"_id": service_object_id},
                {"$set": {"status": "accepted", "accepted_by": actor_email}}
            )
            print(f"Job {job_id} updated to 'accepted' in neighbors_job_collection.")

            # Synchronize the status in the students' services collection
            students_services_collection.update_one(
                {"_id": service_object_id},
                {"$set": {"status": "accepted", "accepted_by": actor_email}},
                upsert=True  # Use upsert to ensure the entry is created if it doesn't exist
            )
            print(f"Job {job_id} status synced to 'accepted' in students_services_collection.")

            return jsonify({"message": "Job accepted successfully"}), 200

        # If the job is not found in either collection
        print(f"Job {job_id} not found or not in 'requested' status in any collection.")
        return jsonify({"error": "Job not found or not in 'requested' status"}), 404

    except Exception as e:
        print(f"Error accepting job: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/services/requests', methods=['GET'])
def get_requested_services():
    """
    API to fetch all requested services for a neighbor, including updated statuses.
    """
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Fetch requested services for the neighbor
        requests = list(neighbors_requested_services_collection.find({"requested_by": email}))

        if not requests:
            return jsonify([]), 200  # Return an empty list if no requests are found

        result = []
        for req in requests:
            try:
                # Ensure service_id is present and valid
                service_id = req.get("service_id")
                if not service_id or not ObjectId.is_valid(service_id):
                    print(f"Invalid or missing service_id: {req}")
                    continue

                # Fetch the current job details from the students' services collection
                job = students_services_collection.find_one({"_id": ObjectId(service_id)})
                if job:
                    # Update service details based on the fetched job data
                    service_details = {
                        "jobTitle": job.get("job_title", "N/A"),  # Updated fallback
                        "jobDescription": job.get("job_description", "N/A"),
                        "hours": job.get("hours", "N/A"),
                        "price": job.get("price", 0.0),
                        "services": job.get("services", []),
                        "postedBy": job.get("email", "Unknown"),
                    }
                    # Update the status if the job exists
                    req["status"] = job.get("status", req.get("status", "pending"))
                else:
                    # Fallback to the original request's service details if the job is not found
                    service_details = req.get("service_details", {
                        "jobTitle": "N/A",
                        "jobDescription": "N/A",
                        "hours": "N/A",
                        "price": 0.0,
                        "services": [],
                        "postedBy": "Unknown",
                    })

                # Add the updated request to the result
                result.append({
                    "request_id": str(req["_id"]),
                    "service_details": service_details,
                    "status": req.get("status", "pending"),  # Include updated status
                })
            except Exception as e:
                print(f"Error processing request {req}: {e}")
                continue

        print("Final Response:", result)  # Debugging to ensure the data structure is correct
        return jsonify(result), 200

    except Exception as e:
        print(f"Error fetching requested services: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/api/students/request_job', methods=['POST'])
def request_job():
    """
    API to allow a student to request a job from a neighbor.
    """
    try:
        data = request.json
        job_id = data.get("jobId")
        student_email = data.get("studentEmail")

        if not job_id or not student_email:
            return jsonify({"error": "Job ID and student email are required"}), 400

        if not ObjectId.is_valid(job_id):
            return jsonify({"error": "Invalid Job ID"}), 400

        job_object_id = ObjectId(job_id)

        # Fetch job details
        job_details = neighbors_job_collection.find_one({"_id": job_object_id})
        if not job_details:
            return jsonify({"error": "Job not found"}), 404

        # Check for duplicate request
        existing_request = students_requested_services_collection.find_one(
            {"job_id": job_object_id, "requested_by": student_email}
        )
        if existing_request:
            return jsonify({"error": "Job already requested"}), 400

        # Insert request into students_requested_services_collection
        request_entry = {
            "job_id": job_object_id,
            "job_details": {
                "job_title": job_details.get("title", "N/A"),
                "job_description": job_details.get("additional_details", "N/A"),
                "hours": job_details.get("hours", 0),
                "price": job_details.get("pay", 0.0),
                "posted_by": job_details.get("posted_by_email", "Unknown"),
            },
            "requested_by": student_email,
            "status": "requested",
        }
        students_requested_services_collection.insert_one(request_entry)

        # Update status in neighbors_job_collection
        neighbors_job_collection.update_one(
            {"_id": job_object_id},
            {"$set": {"status": "requested"}}
        )

        print(f"Job {job_id} requested by {student_email}.")
        return jsonify({"message": "Job requested successfully"}), 201

    except Exception as e:
        print(f"Error requesting job: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/api/students/my-requests', methods=['GET'])
def get_student_requested_jobs():
    """
    API to fetch jobs requested by a student from neighbors, including updated status.
    """
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Fetch the requested jobs by the student
        requests = list(students_requested_services_collection.find({"requested_by": email}))

        if not requests:
            return jsonify([]), 200

        result = []
        for req in requests:
            try:
                # Fetch the service ID and check for updates in the neighbors' job collection
                job_id = req.get("job_id")
                if job_id and ObjectId.is_valid(job_id):
                    # Check for updates in the neighbors' job collection
                    neighbor_job = neighbors_job_collection.find_one({"_id": ObjectId(job_id)})
                    if neighbor_job:
                        # Use the latest status from the neighbors' job collection
                        req["status"] = neighbor_job.get("status", req.get("status", "pending"))

                # Prepare the response object with updated status
                job_details = req.get("job_details", {})
                result.append({
                    "request_id": str(req["_id"]),
                    "service_details": {  # Rename job_details to service_details
                        "job_title": job_details.get("job_title", "N/A"),
                        "job_description": job_details.get("job_description", "N/A"),
                        "hours": job_details.get("hours", "N/A"),
                        "price": job_details.get("price", 0.0),
                        "services": job_details.get("services", []),
                        "posted_by": job_details.get("posted_by", "Unknown"),
                    },
                    "status": req.get("status", "pending"),  # Ensure status reflects latest changes
                })
            except Exception as e:
                print(f"Error processing request {req}: {e}")
                continue

        return jsonify(result), 200

    except Exception as e:
        print(f"Error fetching student-requested jobs: {e}")
        return jsonify({"error": "Internal server error"}), 500



@app.route('/api/services/update-status', methods=['POST'])
def update_service_status():
    try:
        data = request.json
        service_id = data.get("serviceId")
        status = data.get("status")

        if not service_id or not status:
            return jsonify({"error": "Service ID and status are required"}), 400

        if not ObjectId.is_valid(service_id):
            return jsonify({"error": "Invalid Service ID"}), 400

        service_object_id = ObjectId(service_id)

        # Update status in both collections
        neighbor_result = neighbors_requested_services_collection.update_one(
            {"service_id": service_object_id},
            {"$set": {"status": status}}
        )

        student_result = students_services_collection.update_one(
            {"_id": service_object_id},
            {"$set": {"status": status}}
        )

        if neighbor_result.matched_count == 0 and student_result.matched_count == 0:
            return jsonify({"error": "No matching service found in either collection"}), 404

        return jsonify({"message": "Service status updated successfully"}), 200

    except Exception as e:
        print(f"Error updating service status: {e}")
        return jsonify({"error": "Internal server error"}), 500
        
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "sarthaksoccerskate@gmail.com"
APP_PASSWORD = "lqbiijlfytlkdjxr"


@app.route('/api/verify-email', methods=['POST'])
def send_verification_email():
    try:
        data = request.json
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        verification_code = "123456"  # Replace with generated code logic

        # Setup the email details
        sender_email = "sarthaksoccerskate@gmail.com"
        sender_password = "pizw cpys iiat bpix"  # App password
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        subject = "Your Verification Code"
        body = f"Your verification code is: {verification_code}"

        # Send email
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, [email], msg.as_string())

        return jsonify({"message": "Verification code sent successfully"}), 200

    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
        return jsonify({"error": "Failed to send verification email. Please check your SMTP configuration."}), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/api/validate-code', methods=['POST'])
def validate_code():
    try:
        # Parse email and code from the request body
        data = request.get_json()
        email = data.get("email")
        code = data.get("code")
        if not email or not code:
            return jsonify({"error": "Email and code are required"}), 400

        # Check if the code is valid and not expired
        verification_entry = verification_collection.find_one({"email": email, "code": code})
        if not verification_entry:
            return jsonify({"error": "Invalid verification code."}), 400

        # Check expiration
        if datetime.utcnow() > verification_entry["expires_at"]:
            return jsonify({"error": "Verification code has expired."}), 400

        # Optional: delete the verification entry after successful validation
        verification_collection.delete_one({"_id": verification_entry["_id"]})

        return jsonify({"message": "Email verified successfully."}), 200

    except Exception as e:
        print(f"Error validating code: {e}")
        return jsonify({"error": "Failed to validate verification code."}), 500

from flask import Flask, request, jsonify
from kafka import KafkaProducer, KafkaConsumer
from flask_socketio import SocketIO, emit
import threading
import json

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Kafka producer configuration
producer_config = {
    'bootstrap_servers': 'kafka:9092'  # Kafka service name defined in docker-compose
}
producer = KafkaProducer(**producer_config)

# Kafka Consumer setup (runs in a separate thread)
def consume_messages():
    consumer = KafkaConsumer(
        'test-topic',  # Topic to listen for messages
        group_id='consumer-group',
        bootstrap_servers=['kafka:9092'],
        auto_offset_reset='earliest'
    )

    for message in consumer:
        # Parse the consumed message and emit it to WebSocket clients
        notification = message.value.decode('utf-8')
        socketio.emit('notification', {'message': notification, 'timestamp': 'Now'}, broadcast=True)

# Start the consumer in a separate thread
threading.Thread(target=consume_messages, daemon=True).start()

# Route to produce a message to Kafka
@app.route('/api/kafka/produce', methods=['POST'])
def produce_message():
    try:
        data = request.json
        topic = data.get('topic', 'test-topic')  # Default topic
        message = data.get('message', 'Hello Kafka!')

        if not topic or not message:
            return jsonify({"error": "Topic and message are required"}), 400

        producer.produce(topic, value=message.encode('utf-8'))
        producer.flush()
        return jsonify({"message": f"Message '{message}' sent to topic '{topic}'"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
