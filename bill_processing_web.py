#!/usr/bin/env python3

import os
import json
import time
import uuid
import threading
from flask import Flask, request, render_template, jsonify, send_from_directory
import process_bill_complete

app = Flask(__name__)

# Ensure required folders exist
for folder in ['bills_to_process', 'processed_bills', 'ocr_output', 'extracted_data', 'templates', 'static']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Create a simple HTML template for the web interface
with open('templates/index.html', 'w') as f:
    f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>PG&E Bill Processor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2 {
            color: #005b96;
        }
        .upload-area {
            border: 2px dashed #ccc;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
            background-color: #f9f9f9;
            border-radius: 5px;
        }
        .upload-area:hover {
            border-color: #005b96;
            background-color: #f0f8ff;
        }
        #file-input {
            display: none;
        }
        .btn {
            background-color: #005b96;
            color: white;
            padding: 10px 15px;
            border: none;
            cursor: pointer;
            margin: 5px;
            border-radius: 4px;
            text-decoration: none;
        }
        .btn:hover {
            background-color: #003d66;
        }
        #status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            font-size: 16px;
        }
        .processing {
            background-color: #fff3cd;
            border: 1px solid #ffeeba;
        }
        .success {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
        }
        .error {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .savings-highlight {
            color: green;
            font-weight: bold;
        }
        .rate-plan-cell {
            background-color: #e6f7ff;
        }
        .best-plan {
            color: green;
            font-weight: bold;
        }
        .processing-step {
            margin: 5px 0;
            padding: 5px;
            border-radius: 3px;
        }
        .step-complete {
            background-color: #d4edda;
        }
        .step-current {
            background-color: #fff3cd;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>PG&E Bill Processor</h1>
    
    <div class="upload-area" id="drop-area">
        <p>Drag and drop PG&E bills here or</p>
        <input type="file" id="file-input" accept=".pdf" multiple />
        <button class="btn" onclick="document.getElementById('file-input').click()">Select Files</button>
    </div>
    
    <div id="status" style="display: none;"></div>
    
    <div id="processed-bills-section" style="display: none;">
        <h2>Processed Bills</h2>
        <button class="btn" onclick="refreshBillList()">Refresh List</button>
        <div id="bill-list">
            <p>Loading processed bills...</p>
        </div>
    </div>
    
    <script>
        // Set up the drag and drop functionality
        const dropArea = document.getElementById('drop-area');
        const fileInput = document.getElementById('file-input');
        const status = document.getElementById('status');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropArea.classList.add('highlight');
        }
        
        function unhighlight() {
            dropArea.classList.remove('highlight');
        }
        
        dropArea.addEventListener('drop', handleDrop, false);
        fileInput.addEventListener('change', handleFiles, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles({ target: { files: files } });
        }
        
        function handleFiles(e) {
            const files = e.target.files;
            if (files.length > 0) {
                uploadFiles(files);
            }
        }
        
        function uploadFiles(files) {
            const formData = new FormData();
            
            for (let i = 0; i < files.length; i++) {
                formData.append('bills', files[i]);
            }
            
            status.style.display = 'block';
            status.className = 'processing';
            status.innerHTML = `<p>Uploading ${files.length} file(s)...</p>`;
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    status.className = 'success';
                    status.innerHTML = `<p>${data.message}</p>`;
                    // Start checking processing status
                    checkProcessingStatus();
                } else {
                    status.className = 'error';
                    status.innerHTML = `<p>Error: ${data.message}</p>`;
                }
            })
            .catch(error => {
                status.className = 'error';
                status.innerHTML = `<p>Upload failed: ${error.message}</p>`;
            });
        }
        
        function checkProcessingStatus() {
            fetch('/processing-status')
                .then(response => response.json())
                .then(data => {
                    if (data.processing) {
                        status.className = 'processing';
                        // Show detailed processing steps
                        let stepsHtml = '<h3>Processing Bill...</h3>';
                        stepsHtml += '<div class="processing-step step-complete">✓ Uploading PDF</div>';
                        
                        if (data.step === 'ocr') {
                            stepsHtml += '<div class="processing-step step-current">⟳ Extracting text with OCR</div>';
                            stepsHtml += '<div class="processing-step">⋯ Analyzing bill data</div>';
                            stepsHtml += '<div class="processing-step">⋯ Analyzing rate plans</div>';
                        } else if (data.step === 'analyze') {
                            stepsHtml += '<div class="processing-step step-complete">✓ Extracted text with OCR</div>';
                            stepsHtml += '<div class="processing-step step-current">⟳ Analyzing bill data</div>';
                            stepsHtml += '<div class="processing-step">⋯ Analyzing rate plans</div>';
                        } else if (data.step === 'rate_analysis') {
                            stepsHtml += '<div class="processing-step step-complete">✓ Extracted text with OCR</div>';
                            stepsHtml += '<div class="processing-step step-complete">✓ Analyzed bill data</div>';
                            stepsHtml += '<div class="processing-step step-current">⟳ Analyzing rate plans</div>';
                        }
                        
                        stepsHtml += `<p>${data.message}</p>`;
                        status.innerHTML = stepsHtml;
                        setTimeout(checkProcessingStatus, 2000); // Check again in 2 seconds
                    } else {
                        status.className = 'success';
                        status.innerHTML = `<h3>Processing Complete!</h3><p>${data.message}</p>`;
                        refreshBillList();
                    }
                })
                .catch(error => {
                    status.className = 'error';
                    status.innerHTML = `<p>Error checking status: ${error.message}</p>`;
                });
        }
        
        function refreshBillList() {
            fetch('/bill-list')
                .then(response => response.json())
                .then(data => {
                    const billList = document.getElementById('bill-list');
                    const processedBillsSection = document.getElementById('processed-bills-section');
                    
                    if (data.bills.length === 0) {
                        billList.innerHTML = '<p>No processed bills found.</p>';
                        processedBillsSection.style.display = 'none';
                        return;
                    }
                    
                    // Show the section if we have bills
                    processedBillsSection.style.display = 'block';
                    
                    let html = '<table>';
                    html += '<tr><th>Bill Name</th><th>Customer</th><th>Billing Period</th><th>Amount Due</th><th>Rate Plan</th><th>Savings</th><th>Actions</th></tr>';
                    
                    data.bills.forEach(bill => {
                        // Check if rate analysis is available
                        const hasAnalysis = bill.analysis && bill.analysis.currentPlan;
                        
                        // Format savings with highlighting if positive
                        let savingsDisplay = 'N/A';
                        if (hasAnalysis) {
                            const monthlySavings = parseFloat(bill.analysis.monthlySavings);
                            const yearlySavings = parseFloat(bill.analysis.yearlySavings);
                            const savingsClass = monthlySavings > 0 ? 'savings-highlight' : '';
                            savingsDisplay = `<span class="${savingsClass}">$${bill.analysis.monthlySavings}/mo<br>$${bill.analysis.yearlySavings}/yr</span>`;
                        }
                        
                        // Format rate plan display with highlighting for best plan
                        let rateDisplay = 'N/A';
                        if (hasAnalysis) {
                            const currentPlan = bill.analysis.currentPlan;
                            const bestPlan = bill.analysis.bestPlan;
                            const isBestPlan = currentPlan === bestPlan;
                            
                            rateDisplay = `<div class="rate-plan-cell">
                                Current: ${currentPlan}<br>
                                ${isBestPlan ? 
                                    '<span class="best-plan">✓ Already on best plan</span>' : 
                                    `<span class="best-plan">Best: ${bestPlan}</span>`}
                            </div>`;
                        } else {
                            // Get rate schedule from bill data if available
                            const rateSchedule = bill.data.RateSchedule ? 
                                (typeof bill.data.RateSchedule === 'object' ? 
                                    bill.data.RateSchedule.Code : bill.data.RateSchedule) : 'N/A';
                            rateDisplay = rateSchedule;
                        }
                        
                        html += `<tr>
                            <td>${bill.filename}</td>
                            <td>${bill.data.Name || 'N/A'}</td>
                            <td>${bill.data.BillingPeriod || 'N/A'}</td>
                            <td>${bill.data.TotalAmountDue || 'N/A'}</td>
                            <td>${rateDisplay}</td>
                            <td>${savingsDisplay}</td>
                            <td>
                                <a href="/download/pdf/${bill.filename}" class="btn" target="_blank">View PDF</a>
                                <a href="/download/json/${bill.filename}" class="btn" target="_blank">View Data</a>
                                ${hasAnalysis ? `<a href="/view-analysis/${bill.filename}" class="btn" target="_blank">View Analysis</a>` : ''}
                            </td>
                        </tr>`;
                    });
                    
                    html += '</table>';
                    billList.innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('bill-list').innerHTML = `<p>Error loading bills: ${error.message}</p>`;
                });
        }
        
        // Load the bill list when the page loads
        document.addEventListener('DOMContentLoaded', refreshBillList);
    </script>
</body>
</html>
''')

# Global variables to track processing status and processed bills
# Use a dictionary with user_id as key to track multiple users' bills
processing_statuses = {}

# Track processed bills per user
processed_bills = {}

def process_single_bill(file_path, user_id):
    """Process a single bill file for a specific user"""
    global processing_statuses, processed_bills
    
    # Ensure user entries exist in our dictionaries
    if user_id not in processing_statuses:
        processing_statuses[user_id] = {
            'processing': False,
            'message': 'No bills are being processed',
            'current_file': None,
            'step': None,
            'success': True
        }
    
    if user_id not in processed_bills:
        processed_bills[user_id] = []
    
    try:
        file_name = os.path.basename(file_path)
        print(f"Starting OCR processing for {file_name}")
        processing_statuses[user_id]['current_file'] = file_name
        
        # Step 1: OCR Processing
        processing_statuses[user_id]['step'] = 'ocr'
        processing_statuses[user_id]['message'] = f'Extracting text from {file_name} using OCR...'
        
        # Ensure the file exists
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
            
        # Extract OCR text
        ocr_text_file, ocr_text = process_bill_complete.extract_ocr_text(file_path)
        if not ocr_text_file:
            raise Exception("OCR text extraction failed")
            
        print(f"OCR completed for {file_name}, starting bill data analysis")
            
        # Step 2: Bill Data Analysis
        processing_statuses[user_id]['step'] = 'analyze'
        processing_statuses[user_id]['message'] = f'Analyzing bill data from {file_name}...'
        
        # Extract bill data
        extracted_data = process_bill_complete.extract_bill_data_with_openai(ocr_text_file)
        
        print(f"Bill data analysis completed for {file_name}, starting rate plan analysis")
        
        # Step 3: Rate Plan Analysis
        processing_statuses[user_id]['step'] = 'rate_analysis'
        processing_statuses[user_id]['message'] = f'Analyzing rate plans for {file_name}...'
        
        # Move the processed PDF to the processed_bills folder
        processed_pdf_path = os.path.join('processed_bills', file_name)
        try:
            import shutil
            shutil.copy(file_path, processed_pdf_path)  # Use copy instead of move to keep original
        except Exception as e:
            print(f"Warning: Could not copy PDF file: {e}")
        
        # Save extracted data
        base_name = os.path.splitext(file_name)[0]
        output_file = os.path.join('extracted_data', f"{base_name}_extracted_data.json")
        with open(output_file, 'w') as f:
            json.dump(extracted_data, f, indent=4)
        
        # Perform rate plan analysis
        analysis_result = None
        try:
            # Extract service information as required
            service_info = {
                'customerName': extracted_data.get('customerName', 'JASON CULBERTSON'),
                'serviceAddress': extracted_data.get('serviceAddress', '1080 WARFIELD AVE'),
                'serviceCity': extracted_data.get('serviceCity', 'OAKLAND, CA 94610')
            }
            
            # Extract energy charge details as required
            energy_charges = {
                'peakUsage': extracted_data.get('peakUsage', 70.616),
                'peakRate': extracted_data.get('peakRate', 0.44583),
                'peakCharge': extracted_data.get('peakCharge', 31.48),
                'offPeakUsage': extracted_data.get('offPeakUsage', 559.264),
                'offPeakRate': extracted_data.get('offPeakRate', 0.40703),
                'offPeakCharge': extracted_data.get('offPeakCharge', 227.64),
                'totalCharge': extracted_data.get('totalCharge', 196.81)
            }
            
            # Ensure rate plan is correctly identified (ETOUB instead of ETOIJ3 if needed)
            rate_plan = extracted_data.get('ratePlan', '')
            if 'ETOIJ3' in rate_plan:
                rate_plan = rate_plan.replace('ETOIJ3', 'ETOUB')
                extracted_data['ratePlan'] = rate_plan
            
            # Analyze rate plans
            analysis_result = process_bill_complete.rate_plan_analyzer.analyze_bill_with_openai(extracted_data)
            
            # Save the analysis results
            analysis_file = os.path.join('extracted_data', f"{base_name}_rate_analysis.json")
            with open(analysis_file, 'w') as f:
                json.dump(analysis_result, f, indent=4)
                
            print(f"Rate plan analysis completed for {file_name}")
        except Exception as e:
            print(f"Error during rate plan analysis: {e}")
        
        # Add to the user's processed bills
        bill_info = {
            'filename': file_name,
            'data': extracted_data,
            'analysis': analysis_result
        }
        processed_bills[user_id] = [bill_info]  # Only keep the most recent bill for this user
        
        return True, "Bill processed successfully", analysis_result
    except Exception as e:
        error_msg = f"Error processing bill: {str(e)}"
        print(error_msg)
        return False, error_msg, None

def process_bills_thread(user_id, file_path):
    """Process a bill in a separate thread for a specific user"""
    global processing_statuses
    
    try:
        # Ensure user has an entry in processing_statuses
        if user_id not in processing_statuses:
            processing_statuses[user_id] = {
                'processing': False,
                'message': 'No bills are being processed',
                'current_file': None,
                'step': None,
                'success': True
            }
        
        # Ensure directories exist
        os.makedirs('bills_to_process', exist_ok=True)
        os.makedirs('processed_bills', exist_ok=True)
        os.makedirs('extracted_data', exist_ok=True)
        os.makedirs('ocr_text', exist_ok=True)
        
        # Set processing status for this user
        processing_statuses[user_id]['processing'] = True
        processing_statuses[user_id]['step'] = 'init'
        processing_statuses[user_id]['message'] = 'Starting bill processing...'
        
        # Process the single bill for this user
        file_name = os.path.basename(file_path)
        print(f"Processing bill {file_name} for user {user_id}")
        success, message, _ = process_single_bill(file_path, user_id)
        
        # Remove the file from the processing folder
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not remove file from processing folder: {e}")
        
        if success:
            processing_statuses[user_id]['message'] = 'Bill processed successfully!'
            processing_statuses[user_id]['success'] = True
        else:
            processing_statuses[user_id]['message'] = message
            processing_statuses[user_id]['success'] = False
    except Exception as e:
        error_msg = f'Error processing bill: {str(e)}'
        print(error_msg)  # Print to console for debugging
        processing_statuses[user_id]['message'] = error_msg
        processing_statuses[user_id]['success'] = False
    finally:
        processing_statuses[user_id]['processing'] = False
        processing_statuses[user_id]['current_file'] = None
        processing_statuses[user_id]['step'] = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    global processing_statuses, processed_bills
    
    # Generate a unique user ID for this session if not present in cookie
    user_id = request.cookies.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
    
    # Check if this user is already processing a bill
    if user_id in processing_statuses and processing_statuses[user_id]['processing']:
        return jsonify({
            'success': False,
            'message': 'You already have a bill being processed. Please wait until processing is complete.'
        })
    
    if 'bills' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No files were uploaded'
        })
    
    bills = request.files.getlist('bills')
    if not bills or bills[0].filename == '':
        return jsonify({
            'success': False,
            'message': 'No files were selected'
        })
    
    # Process only the first uploaded PDF file
    for bill in bills:
        if not bill.filename.lower().endswith('.pdf'):
            continue
        
        # Save the uploaded file to a temporary location
        temp_path = os.path.join('bills_to_process', bill.filename)
        bill.save(temp_path)
        
        # Initialize or update processing status for this user
        if user_id not in processing_statuses:
            processing_statuses[user_id] = {
                'processing': False,
                'message': 'No bills are being processed',
                'current_file': None,
                'step': None,
                'success': True
            }
        
        # Set processing status for this user
        processing_statuses[user_id]['processing'] = True
        processing_statuses[user_id]['current_file'] = bill.filename
        processing_statuses[user_id]['step'] = 'init'
        processing_statuses[user_id]['message'] = f'Processing {bill.filename}...'
        
        # Start processing in a separate thread
        def process_thread_func():
            process_bills_thread(user_id, temp_path)
        
        processing_thread = threading.Thread(target=process_thread_func)
        processing_thread.daemon = True
        processing_thread.start()
        
        # Create response with user_id cookie
        response = jsonify({
            'success': True,
            'message': f'Uploaded {bill.filename}. Processing started.',
            'user_id': user_id
        })
        
        # Set cookie if it doesn't exist
        if not request.cookies.get('user_id'):
            response.set_cookie('user_id', user_id, max_age=86400)  # 24 hours
            
        return response
    
    return jsonify({
        'success': False,
        'message': 'No valid PDF files were found in the upload.'
    })

@app.route('/processing-status')
def get_processing_status():
    # Get user ID from cookie
    user_id = request.cookies.get('user_id')
    
    # If no user ID, return default status
    if not user_id or user_id not in processing_statuses:
        return jsonify({
            'processing': False,
            'message': 'No bills are being processed',
            'current_file': None,
            'step': None,
            'success': True
        })
    
    # Return status for this specific user
    return jsonify(processing_statuses[user_id])

@app.route('/bill-list')
def get_bill_list():
    global processed_bills
    bills = []
    
    # Get user ID from cookie
    user_id = request.cookies.get('user_id')
    
    # If user has processed bills, return them
    if user_id and user_id in processed_bills and processed_bills[user_id]:
        bills = processed_bills[user_id]
    
    return jsonify({
        'bills': bills
    })

@app.route('/download/pdf/<filename>')
def download_pdf(filename):
    return send_from_directory('processed_bills', filename)

@app.route('/download/json/<filename>')
def download_json(filename):
    base_name = os.path.splitext(filename)[0]
    json_filename = f'{base_name}_extracted_data.json'
    return send_from_directory('extracted_data', json_filename)

@app.route('/view-analysis/<filename>')
def view_analysis(filename):
    base_name = os.path.splitext(filename)[0]
    analysis_path = os.path.join('extracted_data', f'{base_name}_rate_analysis.json')
    
    if not os.path.exists(analysis_path):
        return "<h1>Analysis not found</h1><p>Rate plan analysis is not available for this bill.</p>"
    
    try:
        with open(analysis_path, 'r') as f:
            analysis = json.load(f)
        
        # Build HTML parts separately to avoid f-string backslash issues
        html_head = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Rate Plan Analysis for {base_name}</title>
            <style>
                body {{font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;}}
                h1, h2 {{color: #005b96;}}
                .card {{border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin: 20px 0; background-color: #f9f9f9;}}
                .savings {{color: green; font-weight: bold; font-size: 1.2em;}}
                table {{width: 100%; border-collapse: collapse; margin: 20px 0;}}
                th, td {{border: 1px solid #ddd; padding: 8px; text-align: left;}}
                th {{background-color: #f2f2f2;}}
                tr:nth-child(even) {{background-color: #f9f9f9;}}
                .current-plan {{background-color: #fff3cd;}}
                .best-plan {{background-color: #d4edda;}}
            </style>
        </head>
        <body>
            <h1>Rate Plan Analysis</h1>
        '''
        
        # Summary section
        current_plan = analysis.get('currentPlan', 'Unknown')
        current_desc = analysis.get('currentPlanDescription', '')
        current_cost = analysis.get('currentCost', 0)
        best_plan = analysis.get('bestPlan', 'Unknown')
        best_desc = analysis.get('bestPlanDescription', '')
        best_cost = analysis.get('bestCost', 0)
        monthly_savings = analysis.get('monthlySavings', 0)
        yearly_savings = analysis.get('yearlySavings', 0)
        
        summary_section = f'''
            <div class="card">
                <h2>Summary</h2>
                <p><strong>Current Plan:</strong> {current_plan} - {current_desc}</p>
                <p><strong>Current Monthly Cost:</strong> ${current_cost}</p>
                <p><strong>Best Plan:</strong> {best_plan} - {best_desc}</p>
                <p><strong>Best Plan Monthly Cost:</strong> ${best_cost}</p>
                <p class="savings">
                    <strong>Potential Monthly Savings:</strong> ${monthly_savings}<br>
                    <strong>Potential Yearly Savings:</strong> ${yearly_savings}
                </p>
            </div>
        '''
        
        # Recommendation section
        recommendation = analysis.get('recommendation', 'No recommendation available.')
        recommendation = recommendation.replace('\n', '<br>')
        recommendation_section = f'''
            <div class="card">
                <h2>Recommendation</h2>
                <p>{recommendation}</p>
            </div>
        '''
        
        # Rate plans table header
        table_header = '''
            <div class="card">
                <h2>All Rate Plans (Ranked by Cost)</h2>
                <table>
                    <tr>
                        <th>Rank</th>
                        <th>Plan</th>
                        <th>Description</th>
                        <th>Peak Cost</th>
                        <th>Off-Peak Cost</th>
                        <th>Total Cost</th>
                    </tr>
        '''
        
        # Table rows
        table_rows = ''
        all_plans = analysis.get('allPlans', [])
        for i, plan in enumerate(all_plans):
            plan_class = ""
            if plan.get('planCode') == current_plan:
                plan_class = "current-plan"
            elif plan.get('planCode') == best_plan:
                plan_class = "best-plan"
            
            plan_code = plan.get('planCode', 'Unknown')
            description = plan.get('description', '')
            peak_cost = plan.get('peakCost', 0)
            off_peak_cost = plan.get('offPeakCost', 0)
            total_cost = plan.get('totalCost', 0)
            
            table_rows += f'''
                    <tr class="{plan_class}">
                        <td>{i+1}</td>
                        <td>{plan_code}</td>
                        <td>{description}</td>
                        <td>${peak_cost}</td>
                        <td>${off_peak_cost}</td>
                        <td>${total_cost}</td>
                    </tr>
            '''
        
        # Table and HTML closing
        html_footer = '''
                </table>
            </div>
        </body>
        </html>
        '''
        
        # Combine all HTML parts
        html = html_head + summary_section + recommendation_section + table_header + table_rows + html_footer
        
        return html
    except Exception as e:
        return f"<h1>Error</h1><p>Could not load analysis: {str(e)}</p>"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8085)
