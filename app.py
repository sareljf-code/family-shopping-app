import os
import json
import uuid
from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from PIL import Image
import io

app = Flask(__name__)

# ==========================================
# CONFIGURATION - ACTION REQUIRED BY USER
# ==========================================
# 1. Google Sheets Setup
# Save your Google Cloud Service Account JSON key as 'service_account.json' in this folder.
SERVICE_ACCOUNT_FILE = 'service_account.json'
SHEET_NAME = 'ShoppingList' # Change this if your sheet is named differently

# 2. Google Gemini API Setup
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# ==========================================
# INITIALIZATION
# ==========================================

def get_sheet():
    """Authenticates with Google Sheets and returns the worksheet."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # In the cloud, we use an environment variable. Locally, we use the file.
        google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        if google_creds_json:
            creds_dict = json.loads(google_creds_json)
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            credentials = Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=scopes
            )
        gc = gspread.authorize(credentials)
        
        # Try to open the sheet. If it doesn't exist, create it?
        # For now, assume it exists and is shared with the service account.
        sh = gc.open(SHEET_NAME)
        worksheet = sh.sheet1
        
        # Ensure headers exist
        if not worksheet.get_all_values():
            worksheet.append_row(["ID", "Name", "Quantity"])
            
        return worksheet
    except Exception as e:
        print(f"Google Sheets Error: {e}")
        return None

# Initialize Gemini
if GEMINI_API_KEY and GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_HERE':
    genai.configure(api_key=GEMINI_API_KEY)
    vision_model = genai.GenerativeModel('gemini-3.6-flash')
else:
    vision_model = None


# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/list', methods=['GET'])
def get_list():
    """Fetches the shopping list from Google Sheets."""
    sheet = get_sheet()
    if not sheet:
        return jsonify([]) # Return empty if no sheet (e.g., not configured yet)
    
    values = sheet.get_all_values()
    if not values:
        return jsonify([])

    # Try to determine if first row is a header
    first_row = [str(x).lower().strip() for x in values[0]]
    has_headers = any(h in ['name', 'item', 'product', 'qty', 'quantity', 'amount'] for h in first_row)
    
    start_idx = 1 if has_headers else 0
    
    valid_categories = [
        "Fruit & Veg.", "Fish & Meat", "Dairy & Eggs", "Bakery & Bread", 
        "Pantry & Dry Goods", "Snacks & Sweets", "Beverages", "Frozen Foods", 
        "Toiletries", "Cleaning", "Pharmacy & Health", "Pet Supplies", "Misc."
    ]
    
    items = []
    # We will use the Google Sheet row number as the unique ID for deletion
    # Row numbers in gspread are 1-indexed
    for i in range(start_idx, len(values)):
        row = values[i]
        if not row:
            continue
            
        # Assume first column is the item name, second column (if exists) is quantity
        name = row[0] if len(row) > 0 else ""
        quantity = row[1] if len(row) > 1 else "1"
        category = row[2] if len(row) > 2 else ""
        
        if name.strip():
            # Retroactively categorize empty items
            if category.strip() == "":
                original_category = category
                category = "Misc."
                if vision_model:
                    try:
                        cat_prompt = f"Categorize this grocery item: '{name}'. It may be in Hebrew. You MUST choose exactly one category from this exact list: [Fruit & Veg., Fish & Meat, Dairy & Eggs, Bakery & Bread, Pantry & Dry Goods, Snacks & Sweets, Beverages, Frozen Foods, Toiletries, Cleaning, Pharmacy & Health, Pet Supplies, Misc.]. Return ONLY the exact string from the list."
                        cat_response = vision_model.generate_content(cat_prompt)
                        detected_cat = cat_response.text.strip().lower()
                        
                        # Robust keyword matching
                        if "fruit" in detected_cat or "veg" in detected_cat or "produce" in detected_cat:
                            category = "Fruit & Veg."
                        elif "fish" in detected_cat or "meat" in detected_cat or "poultry" in detected_cat or "chicken" in detected_cat or "beef" in detected_cat:
                            category = "Fish & Meat"
                        elif "dairy" in detected_cat or "egg" in detected_cat or "milk" in detected_cat or "cheese" in detected_cat:
                            category = "Dairy & Eggs"
                        elif "bakery" in detected_cat or "bread" in detected_cat or "pastry" in detected_cat:
                            category = "Bakery & Bread"
                        elif "pantry" in detected_cat or "dry" in detected_cat or "pasta" in detected_cat or "rice" in detected_cat or "can" in detected_cat:
                            category = "Pantry & Dry Goods"
                        elif "snack" in detected_cat or "sweet" in detected_cat or "candy" in detected_cat or "chocolate" in detected_cat or "chip" in detected_cat:
                            category = "Snacks & Sweets"
                        elif "beverage" in detected_cat or "drink" in detected_cat or "water" in detected_cat or "juice" in detected_cat or "soda" in detected_cat:
                            category = "Beverages"
                        elif "frozen" in detected_cat or "ice" in detected_cat:
                            category = "Frozen Foods"
                        elif "toilet" in detected_cat or "bath" in detected_cat or "personal" in detected_cat or "soap" in detected_cat or "shampoo" in detected_cat:
                            category = "Toiletries"
                        elif "clean" in detected_cat or "detergent" in detected_cat or "wash" in detected_cat:
                            category = "Cleaning"
                        elif "pharmacy" in detected_cat or "health" in detected_cat or "vitamin" in detected_cat or "medicine" in detected_cat:
                            category = "Pharmacy & Health"
                        elif "pet" in detected_cat or "dog" in detected_cat or "cat" in detected_cat:
                            category = "Pet Supplies"
                        else:
                            category = "Misc."
                    except Exception as e:
                        print(f"Sync categorization error: {e}")
                
                # Only save if it actually changed or if it was previously completely empty
                if category != original_category or original_category.strip() == "":
                    try:
                        sheet.update_cell(i + 1, 3, category)
                    except Exception as e:
                        print(f"Sync save error: {e}")

            items.append({
                "id": str(i + 1), # 1-indexed row number
                "name": name,
                "quantity": quantity,
                "category": category
            })
            
    return jsonify(items)

@app.route('/api/add', methods=['POST'])
def add_item():
    """Adds a new item to the Google Sheet."""
    data = request.json
    name = data.get('name')
    quantity = data.get('quantity', 1)
    
    if not name:
        return jsonify({"error": "Name is required"}), 400
        
    # Categorize the item using Gemini
    category = "Misc."
    if vision_model:
        try:
            cat_prompt = f"Categorize this grocery item: '{name}'. It may be in Hebrew. You MUST choose exactly one category from this exact list: [Fruit & Veg., Fish & Meat, Dairy & Eggs, Bakery & Bread, Pantry & Dry Goods, Snacks & Sweets, Beverages, Frozen Foods, Toiletries, Cleaning, Pharmacy & Health, Pet Supplies, Misc.]. Return ONLY the exact string from the list."
            cat_response = vision_model.generate_content(cat_prompt)
            detected_cat = cat_response.text.strip().lower()
            
            # Robust keyword matching
            if "fruit" in detected_cat or "veg" in detected_cat or "produce" in detected_cat:
                category = "Fruit & Veg."
            elif "fish" in detected_cat or "meat" in detected_cat or "poultry" in detected_cat or "chicken" in detected_cat or "beef" in detected_cat:
                category = "Fish & Meat"
            elif "dairy" in detected_cat or "egg" in detected_cat or "milk" in detected_cat or "cheese" in detected_cat:
                category = "Dairy & Eggs"
            elif "bakery" in detected_cat or "bread" in detected_cat or "pastry" in detected_cat:
                category = "Bakery & Bread"
            elif "pantry" in detected_cat or "dry" in detected_cat or "pasta" in detected_cat or "rice" in detected_cat or "can" in detected_cat:
                category = "Pantry & Dry Goods"
            elif "snack" in detected_cat or "sweet" in detected_cat or "candy" in detected_cat or "chocolate" in detected_cat or "chip" in detected_cat:
                category = "Snacks & Sweets"
            elif "beverage" in detected_cat or "drink" in detected_cat or "water" in detected_cat or "juice" in detected_cat or "soda" in detected_cat:
                category = "Beverages"
            elif "frozen" in detected_cat or "ice" in detected_cat:
                category = "Frozen Foods"
            elif "toilet" in detected_cat or "bath" in detected_cat or "personal" in detected_cat or "soap" in detected_cat or "shampoo" in detected_cat:
                category = "Toiletries"
            elif "clean" in detected_cat or "detergent" in detected_cat or "wash" in detected_cat:
                category = "Cleaning"
            elif "pharmacy" in detected_cat or "health" in detected_cat or "vitamin" in detected_cat or "medicine" in detected_cat:
                category = "Pharmacy & Health"
            elif "pet" in detected_cat or "dog" in detected_cat or "cat" in detected_cat:
                category = "Pet Supplies"
            else:
                category = "Misc."
        except Exception as e:
            print(f"Categorization error: {e}")

    sheet = get_sheet()
    if sheet:
        # Append name, quantity, and category
        sheet.append_row([name, quantity, category])
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Google Sheets not configured"}), 500

@app.route('/api/remove', methods=['POST'])
def remove_item():
    """Removes an item from the Google Sheet by ID (row number)."""
    data = request.json
    row_num = data.get('id')
    
    if not row_num:
        return jsonify({"error": "ID is required"}), 400
        
    sheet = get_sheet()
    if sheet:
        try:
            sheet.delete_rows(int(row_num))
            return jsonify({"success": True})
        except Exception as e:
            print(f"Delete error: {e}")
            return jsonify({"error": "Item not found or could not delete"}), 404
            
    return jsonify({"error": "Could not remove item"}), 500

@app.route('/api/update_qty', methods=['POST'])
def update_qty():
    """Updates the quantity of an item in the Google Sheet by row number."""
    data = request.json
    row_num = data.get('id')
    new_qty = data.get('quantity')
    
    if not row_num or new_qty is None:
        return jsonify({"error": "ID and new quantity are required"}), 400
        
    sheet = get_sheet()
    if sheet:
        try:
            # update_cell(row, col) is 1-indexed. Quantity is column 2.
            # Convert new_qty to string to avoid gspread formatting issues
            sheet.update_cell(int(row_num), 2, str(new_qty))
            return jsonify({"success": True})
        except Exception as e:
            print(f"Update error: {e}")
            return jsonify({"error": "Could not update item"}), 500
            
    return jsonify({"error": "Google Sheets not configured"}), 500

@app.route('/api/vision', methods=['POST'])
def analyze_image():
    """Receives an image, sends to Gemini, returns product name."""
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
        
    if not vision_model:
        return jsonify({"error": "Gemini API key not configured"}), 500

    file = request.files['image']
    try:
        # Read image
        img_bytes = file.read()
        image = Image.open(io.BytesIO(img_bytes))
        
        # Send to Gemini
        prompt = "Look at this image and extract the name of the main grocery or shopping product. The product name or text on the package may be in Hebrew or English. Return ONLY the name of the product, nothing else. Keep it brief and do not include any extra sentences."
        response = vision_model.generate_content([prompt, image])
        
        product_name = response.text.strip()
        
        return jsonify({"productName": product_name})
    except Exception as e:
        print(f"Vision API Error: {e}")
        return jsonify({"error": "Failed to analyze image"}), 500

if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=5001, debug=True)
