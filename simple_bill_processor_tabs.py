#!/usr/bin/env python3

import os
import json
import time
import uuid
import threading
import shutil
from flask import Flask, request, render_template_string, jsonify, send_from_directory
import process_bill_complete

app = Flask(__name__)

# Ensure required folders exist
for folder in ['bills_to_process', 'processed_bills', 'ocr_output', 'extracted_data', 'templates', 'static']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Global variables
processing_status = {
    'processing': False,
    'message': 'No bills are being processed',
    'current_file': None,
    'step': None,
    'success': True
}

last_processed_bill = None
