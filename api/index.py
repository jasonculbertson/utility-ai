from flask import Flask, request, render_template, jsonify, send_from_directory
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from simple_bill_processor
from simple_bill_processor import app as flask_app

# For Vercel serverless functions
app = flask_app
