#!/usr/bin/env python3

import os
import json
from datetime import datetime
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def load_rate_plans():
    """Load rate plans from the JSON file"""
    try:
        with open('rate_plans.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading rate plans: {e}")
        return {}

def calculate_cost_for_plan(rate_plan, peak_usage, off_peak_usage):
    """Calculate the cost for a specific rate plan"""
    peak_cost = peak_usage * rate_plan.get('peakRate', 0)
    off_peak_cost = off_peak_usage * rate_plan.get('offPeakRate', 0)
    total_cost = peak_cost + off_peak_cost
    
    return {
        'planCode': rate_plan.get('alias', None),  # Handle aliases like ETOIJ3 -> ETOUB
        'peakCost': round(peak_cost, 2),
        'offPeakCost': round(off_peak_cost, 2),
        'totalCost': round(total_cost, 2)
    }

def analyze_rate_plans(bill_data):
    """Analyze different rate plans for a bill"""
    # Extract usage data from the bill
    try:
        peak_usage = float(bill_data.get('PeakUsage', 0))
        off_peak_usage = float(bill_data.get('OffPeakUsage', 0))
        current_rate_code = None
        
        # Extract the rate code from the bill data
        rate_schedule = bill_data.get('RateSchedule', {})
        if isinstance(rate_schedule, dict):
            current_rate_code = rate_schedule.get('Code', '').split()[0]  # Extract just the code part
        elif isinstance(rate_schedule, str):
            current_rate_code = rate_schedule.split()[0]  # Extract just the code part
            
        # Clean up the rate code (handle OCR misreads)
        if current_rate_code == 'ETOIJ3':
            current_rate_code = 'ETOUB'
            
        # Load rate plans
        rate_plans = load_rate_plans()
        
        # Calculate costs for each plan
        plan_costs = []
        for plan_code, plan_details in rate_plans.items():
            # If this plan is an alias, skip it (we'll calculate the real plan)
            if 'alias' in plan_details:
                continue
                
            cost_data = calculate_cost_for_plan(plan_details, peak_usage, off_peak_usage)
            cost_data['planCode'] = plan_code
            cost_data['description'] = plan_details.get('description', '')
            plan_costs.append(cost_data)
        
        # Sort plans by total cost (ascending)
        sorted_plans = sorted(plan_costs, key=lambda x: x['totalCost'])
        
        # Find the current plan in the list
        current_plan = None
        for plan in sorted_plans:
            if plan['planCode'] == current_rate_code:
                current_plan = plan
                break
        
        # If we couldn't find the current plan, use the first one as a fallback
        if not current_plan and sorted_plans:
            current_plan = sorted_plans[0]
            
        # Best plan is the first one (lowest cost)
        best_plan = sorted_plans[0] if sorted_plans else None
        
        # Calculate savings
        monthly_savings = 0
        yearly_savings = 0
        
        if current_plan and best_plan and current_plan != best_plan:
            monthly_savings = current_plan['totalCost'] - best_plan['totalCost']
            yearly_savings = monthly_savings * 12
        
        return {
            'currentPlan': current_plan,
            'bestPlan': best_plan,
            'monthlySavings': round(monthly_savings, 2),
            'yearlySavings': round(yearly_savings, 2),
            'allPlans': sorted_plans
        }
    except Exception as e:
        print(f"Error analyzing rate plans: {e}")
        return None

def analyze_bill_with_openai(bill_data):
    """Use OpenAI to analyze the bill data and provide recommendations"""
    try:
        # Analyze rate plans
        analysis = analyze_rate_plans(bill_data)
        
        if not analysis:
            return {
                "error": "Could not analyze rate plans"
            }
        
        # Format the analysis for OpenAI
        current_plan = analysis.get('currentPlan', {})
        best_plan = analysis.get('bestPlan', {})
        monthly_savings = analysis.get('monthlySavings', 0)
        yearly_savings = analysis.get('yearlySavings', 0)
        
        # Create a prompt for OpenAI
        prompt = f"""
        Based on the following electricity usage data:
        - Peak Usage: {bill_data.get('PeakUsage', 'N/A')} kWh
        - Off-Peak Usage: {bill_data.get('OffPeakUsage', 'N/A')} kWh
        - Current Rate Plan: {current_plan.get('planCode', 'Unknown')} - {current_plan.get('description', '')}
        - Current Cost: ${current_plan.get('totalCost', 0)}
        
        The most cost-effective rate plan would be:
        - Best Rate Plan: {best_plan.get('planCode', 'Unknown')} - {best_plan.get('description', '')}
        - Best Plan Cost: ${best_plan.get('totalCost', 0)}
        - Monthly Savings: ${monthly_savings}
        - Yearly Savings: ${yearly_savings}
        
        Please provide a brief analysis of why this plan is better and any considerations the customer should be aware of when switching plans.
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an energy consultant helping customers find the most cost-effective electricity rate plan."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        # Extract the recommendation
        recommendation = response.choices[0].message.content
        
        # Return the complete analysis
        return {
            "currentPlan": current_plan.get('planCode', 'Unknown'),
            "currentPlanDescription": current_plan.get('description', ''),
            "currentCost": current_plan.get('totalCost', 0),
            "bestPlan": best_plan.get('planCode', 'Unknown'),
            "bestPlanDescription": best_plan.get('description', ''),
            "bestCost": best_plan.get('totalCost', 0),
            "monthlySavings": monthly_savings,
            "yearlySavings": yearly_savings,
            "recommendation": recommendation,
            "allPlans": analysis.get('allPlans', [])
        }
    except Exception as e:
        print(f"Error analyzing bill with OpenAI: {e}")
        return {
            "error": f"Analysis failed: {str(e)}"
        }

def main():
    # Check if there are any processed bills
    extracted_data_folder = 'extracted_data'
    if not os.path.exists(extracted_data_folder):
        print(f"Error: {extracted_data_folder} directory not found.")
        return
        
    json_files = [f for f in os.listdir(extracted_data_folder) if f.endswith('_extracted_data.json')]
    
    if not json_files:
        print(f"No processed bills found in {extracted_data_folder}.")
        return
    
    # Process the most recent bill
    latest_file = json_files[0]
    latest_time = os.path.getmtime(os.path.join(extracted_data_folder, latest_file))
    
    for file in json_files:
        file_time = os.path.getmtime(os.path.join(extracted_data_folder, file))
        if file_time > latest_time:
            latest_time = file_time
            latest_file = file
    
    # Load the bill data
    bill_path = os.path.join(extracted_data_folder, latest_file)
    print(f"Analyzing bill: {bill_path}")
    
    try:
        with open(bill_path, 'r') as f:
            bill_data = json.load(f)
            
        # Analyze the bill
        analysis = analyze_bill_with_openai(bill_data)
        
        # Save the analysis
        base_name = os.path.splitext(latest_file)[0]
        analysis_file = f"{base_name}_rate_analysis.json"
        analysis_path = os.path.join(extracted_data_folder, analysis_file)
        
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=4)
            
        print("\nRate Plan Analysis:")
        print("====================")
        print(f"Current Plan: {analysis['currentPlan']} - {analysis['currentPlanDescription']}")
        print(f"Current Cost: ${analysis['currentCost']}")
        print(f"Best Plan: {analysis['bestPlan']} - {analysis['bestPlanDescription']}")
        print(f"Best Cost: ${analysis['bestCost']}")
        print(f"Estimated Monthly Savings: ${analysis['monthlySavings']}")
        print(f"Estimated Yearly Savings: ${analysis['yearlySavings']}")
        print("\nRecommendation:")
        print(analysis['recommendation'])
        
        print(f"\nAnalysis saved to: {analysis_path}")
        
    except Exception as e:
        print(f"Error processing bill: {e}")

if __name__ == "__main__":
    main()
