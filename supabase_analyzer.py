import os
import time
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from openai import AsyncOpenAI
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

if not all([supabase_url, supabase_key, openai_key]):
    raise ValueError("Missing credentials. Please check your .env file")

# Initialize clients
supabase = create_client(supabase_url, supabase_key)
openai_client = AsyncOpenAI(api_key=openai_key)

# Template for OpenAI analysis optimized for GPT-3.5
ANALYSIS_TEMPLATE = """
Analyze this dog food and provide a score (0-100) and brief reasoning for each category. Use these scoring guidelines:

Scoring Guide:
Start at 100 and AGGRESSIVELY deduct points for issues. Be very critical.

Category-Specific Guidelines:

1. PROTEIN Score (start at 100)
   - Named meat first ingredient? Keep 100
   - Multiple quality meat sources in top 3? Keep 100
   - Named meat after 3rd ingredient? (-5)
   - Generic meat terms in first 3? (-20)
   - Generic meat terms after 3rd? (-8)
   - By-products in first 5? (-25)
   - By-products after 5th? (-10)
   - Non-meat protein first? (-35)
   - Multiple fillers before first meat? (-40)
   - BONUS: 3+ named meat sources? (+5)

2. FAT Score (start at 100)
   - Named animal fats in first half? Keep 100
   - Named fats in second half? (-10)
   - Generic animal fat in first half? (-30)
   - Generic fat in second half? (-15)
   - Unnamed fats in first half? (-40)
   - Unnamed fats in second half? (-20)
   - Low-quality fats in first half? (-50)
   - Low-quality fats in second half? (-25)

3. FIBER Score (start at 100)
   - Natural whole food fiber? Keep 100
   - Processed fiber sources? (-20)
   - Cellulose or wood fiber? (-40)

4. CALORIES Score (start at 100)
   - Appropriate density? Keep 100
   - Too high/low? (-25)
   - Excessive fillers? (-40)

5. OMEGA-6 Score (start at 100)
   - Named sources? Keep 100
   - Generic sources? (-10)
   - Missing sources? (-20)

6. ADDITIVES Score (start at 100)
   - Natural only? Keep 100
   - Common preservatives (mixed tocopherols, citric acid)? (+2)
   - Natural flavors? (-3)
   - Artificial colors? (-30)
   - Artificial flavors? (-20)
   - Multiple artificial additives? (-35)
   - BONUS: Contains probiotics/prebiotics? (+3)
   - BONUS: Contains joint supplements? (+2)

7. ORGANIC Score (start at 100)
   - Certified organic? Keep 100
   - Natural ingredients? (-5)
   - Conventional ingredients? (-10)
   - Heavily processed? (-20)

8. HARMFUL INGREDIENTS (start at 100)
   - Clean ingredients only? Keep 100
   - By-products in first 5? (-20)
   - By-products after 5th? (-8)
   - Artificial colors/flavors in first half? (-25)
   - Artificial colors/flavors in second half? (-8)
   - Carrageenan in first 5? (-25)
   - Carrageenan after 5th? (-12)
   - Multiple fillers in first 5 ingredients? (-15)
   - Common binders/thickeners after first 5? (-0)
   - Natural preservatives (mixed tocopherols)? (+2)
   - Combination of above in first 5? (-30)
   - Combination of above after 5th? (-12)
   - BONUS: All natural preservatives? (+3)

9. HEALTH RISKS (start at 100)
   - No known risks? Keep 100
   - Minor concerns? (-3)
   - Major concerns? (-12)
   - Multiple risks? (-20)
   - BONUS: Contains health-promoting ingredients? (+5)
   - BONUS: Contains antioxidants? (+3)

10. OVERALL Score
    Calculate weighted average of scores:
    - Harmful ingredients score counts TWICE in the average
    - All other scores count once
    - Example: if harmful score is 80 and all others are 100:
      (100 + 100 + 100 + 100 + 100 + 100 + 100 + 80 + 80 + 100) / 10 = 96
    - Round to nearest whole number
    
    For the overall reasoning:
    1. Start with the food's biggest strength (e.g. "Excellent protein from named meats")
    2. Add 1-2 key positive features (e.g. "rich in omega-3s, includes probiotics")
    3. Note any harmful ingredients first if score < 95
    4. Be specific about ingredients when possible

IMPORTANT:
1. Every category starts at 100
2. Only subtract points for clear issues
3. When in doubt, keep the score high
4. Common preservatives are fine

Product: {title}
Ingredients: {ingredients}
Caloric Content: {calories}
Guaranteed Analysis: {analysis}

Provide analysis in this exact JSON format:
{{
  "PROTEIN": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "FAT": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "FIBER": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "CALORIES": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "OMEGA-6": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "ADDITIVES": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "ORGANIC/NATURAL": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "HARMFUL INGREDIENTS": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "HEALTH RISKS": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }},
  "OVERALL": {{
    "score": [0-100 number],
    "reasoning": "[50-200 char explanation]"  
  }}
}}

Scoring Rules:
1. ALL scores must be integers between 0-100
2. If data is missing, use score 65 (average)
3. Keep each reasoning between 50-200 chars
4. Heavily penalize fillers using the guide above
5. Focus on ingredient order (first 5 most important)
6. High protein from quality sources should score 85+
7. Natural preservatives preferred over artificial
8. Multiple fillers should compound penalties
"""

def fetch_table_data(table_name):
    """Fetch specific products from Supabase table"""
    try:
        print("Fetching products with null scores but have ingredients...")
        query = supabase.table(table_name).select("*").is_('overall_score', 'null').not_.is_('ingredients', 'null')
        print("Query built successfully")
        
        response = query.execute()
        print(f"Query executed. Response type: {type(response)}")
        
        if hasattr(response, 'data'):
            print(f"Data retrieved. Number of records: {len(response.data)}")
            return response.data
        else:
            print(f"Unexpected response structure: {response}")
            return None
    except Exception as e:
        print(f"Error fetching data from {table_name}: {e}")
        print(f"Error type: {type(e)}")
        return None

async def calculate_weighted_score(scores):
    """Calculate weighted average score with equal weights"""
    total = (
        scores['protein_score'] +
        scores['fat_score'] +
        scores['fiber_score'] +
        scores['calorie_score'] +
        scores['omega_6_score'] +
        scores['additives_score'] +
        scores['organic_score'] +
        scores['harmful_ingredients_score'] +  # Equal weight
        scores['health_risks_score']
    )
    # Divide by 9 since all scores have equal weight
    return round(total / 9)

async def analyze_pet_food_with_openai(product_data):
    """Analyze pet food data using OpenAI's API asynchronously"""
    try:
        print(f"\nAnalyzing product {product_data.get('id')}:")
        
        # Check for missing or invalid ingredients
        ingredients = product_data.get('ingredients', '')
        if not ingredients or ingredients.lower() in ['not available', 'n/a', 'none']:
            print(f"Skipped: Missing ingredients")
            return None
            
        # Set default values for missing data
        analysis = product_data.get('guaranteed_analysis', 'Not available')
        calories = product_data.get('caloric_count', 'Not available')
        
        print(f"Ingredients present: {len(ingredients)} chars")
        print(f"Analysis: {'Present' if analysis != 'Not available' else 'Missing'}") 
        print(f"Calories: {'Present' if calories != 'Not available' else 'Missing'}")

        # Prepare the prompt with product data
        prompt = ANALYSIS_TEMPLATE.format(
            title=product_data['product_title'],
            ingredients=ingredients,
            calories=product_data.get('caloric_count', 'Not provided'),
            analysis=analysis
        )

        # Get analysis from OpenAI
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Faster and more cost-effective
            messages=[
                {"role": "system", "content": "You are a pet nutrition expert. Provide concise, evidence-based analysis."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error analyzing pet food with OpenAI: {e}")
        print(f"Error type: {type(e)}")
        return None

async def update_product_scores(product_id, analysis):
    """Update product scores in the database"""
    try:
        print(f"\nUpdating scores for product {product_id}:")
        print("Analysis keys present:", list(analysis.keys()))
        
        # Map the OpenAI analysis keys to database column names
        update_data = {
            'protein_score': analysis['PROTEIN']['score'],
            'protein_reasoning': analysis['PROTEIN']['reasoning'],
            'fat_score': analysis['FAT']['score'],
            'fat_reasoning': analysis['FAT']['reasoning'],
            'fiber_score': analysis['FIBER']['score'],
            'fiber_reasoning': analysis['FIBER']['reasoning'],
            'calorie_score': analysis['CALORIES']['score'],
            'calorie_reasoning': analysis['CALORIES']['reasoning'],
            'omega_6_score': analysis['OMEGA-6']['score'],
            'omega_6_reasoning': analysis['OMEGA-6']['reasoning'],
            'additives_score': analysis['ADDITIVES']['score'],
            'additives_reasoning': analysis['ADDITIVES']['reasoning'],
            'organic_score': analysis['ORGANIC/NATURAL']['score'],
            'organic_reasoning': analysis['ORGANIC/NATURAL']['reasoning'],
            'harmful_ingredients_score': analysis['HARMFUL INGREDIENTS']['score'],
            'harmful_ingredients_reasoning': analysis['HARMFUL INGREDIENTS']['reasoning'],
            'health_risks_score': analysis['HEALTH RISKS']['score'],
            'health_risks_reasoning': analysis['HEALTH RISKS']['reasoning']
        }
        print("Update data prepared successfully")
        
        # Calculate weighted overall score
        update_data['overall_score'] = await calculate_weighted_score({
            'protein_score': analysis['PROTEIN']['score'],
            'fat_score': analysis['FAT']['score'],
            'fiber_score': analysis['FIBER']['score'],
            'calorie_score': analysis['CALORIES']['score'],
            'omega_6_score': analysis['OMEGA-6']['score'],
            'additives_score': analysis['ADDITIVES']['score'],
            'organic_score': analysis['ORGANIC/NATURAL']['score'],
            'harmful_ingredients_score': analysis['HARMFUL INGREDIENTS']['score'],
            'health_risks_score': analysis['HEALTH RISKS']['score']
        })
        
        # Use the OpenAI reasoning but ensure harmful ingredients are mentioned first if score is low
        harmful_score = analysis['HARMFUL INGREDIENTS']['score']
        if harmful_score < 95:
            update_data['overall_reasoning'] = f"{analysis['HARMFUL INGREDIENTS']['reasoning']}. {analysis['OVERALL']['reasoning']}"
        else:
            update_data['overall_reasoning'] = analysis['OVERALL']['reasoning']
        
        # Validate all scores are numbers
        for key, value in update_data.items():
            if '_score' in key and not isinstance(value, (int, float)):
                raise ValueError(f"Invalid score for {key}: {value}")
        
        # Ensure all text fields are strings and not too long
        for key, value in update_data.items():
            if '_reasoning' in key:
                if not isinstance(value, str):
                    update_data[key] = str(value)
                if len(value) > 1000:  # Assuming max length of 1000 chars
                    update_data[key] = value[:997] + '...'
        
        try:
            result = supabase.table('chewy_products').update(update_data).eq('id', product_id).execute()
            if hasattr(result, 'data') and result.data:
                return True
            else:
                print(f"No data returned from update operation for product {product_id}")
                return False
        except Exception as db_error:
            print(f"Database error for product {product_id}: {str(db_error)}")
            print(f"Update data that failed: {json.dumps(update_data, indent=2)}")
            return False
            
    except KeyError as ke:
        print(f"Missing key in analysis for product {product_id}: {str(ke)}")
        print(f"Available keys: {list(analysis.keys())}")
        return False
    except Exception as e:
        print(f"Unexpected error for product {product_id}: {str(e)}")
        return False

async def process_product(product):
    """Process a single product asynchronously"""
    try:
        # Check for missing data
        ingredients = product.get('ingredients', '')
        analysis = product.get('guaranteed_analysis', '')
        calories = product.get('caloric_count', '')
        
        # Track missing data
        if not ingredients or ingredients.lower() in ['not available', 'n/a', 'none']:
            missing_ingredients += 1
            products_missing_ingredients.append(product)
        if not analysis or analysis.lower() in ['not available', 'n/a', 'none']:
            missing_analysis += 1
            products_missing_analysis.append(product)
        if not calories or calories.lower() in ['not available', 'n/a', 'none']:
            missing_calories += 1
            products_missing_calories.append(product)
            
        print(f"\nAnalyzing: {product['product_title']}")
        analysis = await analyze_pet_food_with_openai(product)
        
        if not analysis:
            failed_analysis += 1
            print("Analysis failed")
            return False
            
        print("Updating database...")
        success = await update_product_scores(product['id'], analysis)
        if success:
            successful_analysis += 1
            print("Successfully updated product scores in database!")
            return True
        else:
            failed_analysis += 1
            print("Failed to update database.")
            return False
    except Exception as e:
        failed_analysis += 1
        print(f"Error processing product: {e}")
        return False

async def analyze_and_update_scores():
    """Analyze specific pet food records in parallel and update the database with progress tracking"""
    print("Fetching products with IDs 1-10...")
    data = fetch_table_data('chewy_products')
    
    # Track products with missing data
    products_missing_ingredients = []
    products_missing_analysis = []
    products_missing_calories = []
    
    if not data:
        print("No data found")
        return
    
    # Track data quality issues
    total_products = len(data)
    missing_ingredients = 0
    missing_analysis = 0
    missing_calories = 0
    successful_analysis = 0
    failed_analysis = 0
    
    print(f"\nStarting parallel analysis of {total_products} products...\n")
    
    # Create a lock for thread-safe printing
    print_lock = asyncio.Lock()
    
    async def process_with_progress(i, product):
        try:
            async with print_lock:
                print(f"Starting analysis of product {i}/{len(data)}: {product['product_title']}")
            
            analysis = await analyze_pet_food_with_openai(product)
            if analysis:
                async with print_lock:
                    print(f"Analysis complete for product {i}, updating database...")
                success = await update_product_scores(product['id'], analysis)
                async with print_lock:
                    if success:
                        print(f"✓ Successfully processed product {i}: {product['product_title']}")
                        return True
                    else:
                        print(f"✗ Failed to update database for product {i}: {product['product_title']}")
                        return False
            else:
                async with print_lock:
                    print(f"✗ Failed to analyze product {i}: {product['product_title']}")
                return False
        except Exception as e:
            async with print_lock:
                print(f"✗ Error processing product {i}: {product['product_title']} - {str(e)}")
            return False
    
    # Create tasks for parallel processing
    tasks = [process_with_progress(i+1, product) for i, product in enumerate(data)]
    results = await asyncio.gather(*tasks)
    
    total_success = sum(1 for r in results if r)
    total_failed = sum(1 for r in results if not r)
    
    print(f"\nBatch Processing Complete!")
    print(f"\nProcessing Summary:")
    print(f"Total Products: {total_products}")
    print(f"Successfully Analyzed: {total_success}")
    print(f"Failed Analysis: {total_failed}")
    print(f"\nData Quality Issues:")
    print(f"Missing Ingredients: {missing_ingredients}")
    print(f"Missing Guaranteed Analysis: {missing_analysis}")
    print(f"Missing Caloric Content: {missing_calories}")
    
    print("\nDetailed Data Analysis for Selected Products:")
    
    # Sample a few products that had missing data
    sample_products = []
    if products_missing_analysis:
        sample_products.extend(products_missing_analysis[:3])
    if products_missing_ingredients:
        sample_products.extend(products_missing_ingredients[:3])
    if not sample_products and data:
        sample_products = data[:3]  # Take first 3 if no missing data
    
    for product in sample_products:
        print(f"\nProduct: {product['product_title']}")
        print("Ingredients Present:", 'Yes' if product.get('ingredients') else 'No')
        if product.get('ingredients'):
            print(f"Ingredients (first 100 chars): {product.get('ingredients', '')[:100]}...")
        print("\nGuaranteed Analysis Present:", 'Yes' if product.get('guaranteed_analysis') else 'No')
        if product.get('guaranteed_analysis'):
            print(f"Analysis: {product.get('guaranteed_analysis', '')}")
        print("\nCaloric Content Present:", 'Yes' if product.get('caloric_count') else 'No')
        if product.get('caloric_count'):
            print(f"Calories: {product.get('caloric_count', '')}")
        print("-" * 80)
    
    # Get updated scores from database
    response = supabase.table('chewy_products').select('*').lte('id', 7542).gte('id', 3001).order('overall_score', desc=True).limit(20).execute()
    
    print('\nTop 10 Products by Score (New Scoring System):')
    print('-' * 80)
    for product in response.data:
        print(f"\nProduct: {product['product_title']}")
        print(f"Overall Score: {product['overall_score']}")
        print(f"Overall Reasoning: {product['overall_reasoning']}")
        print(f"Protein Score: {product['protein_score']}")
        print(f"Harmful Ingredients Score: {product['harmful_ingredients_score']}")
        print('-' * 40)

def analyze_null_columns():
    """Analyze which columns have null values"""
    print("Fetching all Chewy products data...")
    data = fetch_table_data('chewy_products')
    
    if not data:
        print("No data found")
        return
    
    print(f"\nAnalyzing {len(data)} records for null values...")
    
    null_counts = {}
    total_records = len(data)
    
    # Count nulls in each column
    for record in data:
        for col, value in record.items():
            if value is None:
                null_counts[col] = null_counts.get(col, 0) + 1
    
    # Display results
    print("\nColumns with null values:")
    print("Format: Column Name: Null Count (Percentage)")
    print("-" * 50)
    
    for col, count in sorted(null_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_records) * 100
        print(f"{col}: {count:,} ({percentage:.2f}%)")

def find_null_scores():
    """Find all rows where overall_score is null"""
    try:
        print("Finding rows with null overall_score...")
        query = supabase.table('chewy_products').select('id,product_title,ingredients,guaranteed_analysis,caloric_count').is_('overall_score', 'null').execute()
        
        if hasattr(query, 'data'):
            null_rows = query.data
            print(f"\nFound {len(null_rows)} rows with null overall_score")
            print("\nSample of rows with null scores:")
            for row in null_rows[:10]:  # Show first 10 as sample
                print(f"\nID: {row['id']}")
                print(f"Title: {row['product_title']}")
                print("Has ingredients:", 'Yes' if row.get('ingredients') else 'No')
                print("Has analysis:", 'Yes' if row.get('guaranteed_analysis') else 'No')
                print("Has calories:", 'Yes' if row.get('caloric_count') else 'No')
                print("-" * 80)
            
            # Count data completeness
            has_ingredients = sum(1 for r in null_rows if r.get('ingredients'))
            has_analysis = sum(1 for r in null_rows if r.get('guaranteed_analysis'))
            has_calories = sum(1 for r in null_rows if r.get('caloric_count'))
            
            print(f"\nData Completeness for Null Score Rows:")
            print(f"Total null rows: {len(null_rows)}")
            print(f"Rows with ingredients: {has_ingredients} ({(has_ingredients/len(null_rows))*100:.1f}%)")
            print(f"Rows with analysis: {has_analysis} ({(has_analysis/len(null_rows))*100:.1f}%)")
            print(f"Rows with calories: {has_calories} ({(has_calories/len(null_rows))*100:.1f}%)")
        else:
            print("No data returned from query")
    except Exception as e:
        print(f"Error querying table: {e}")

def main():
    """Main entry point"""
    asyncio.run(analyze_and_update_scores())

if __name__ == "__main__":
    main()
