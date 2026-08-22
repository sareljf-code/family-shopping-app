# Setup Instructions for Family Shopping App

To make the app work with your Google Sheet and Google Gemini, you need to set up two things: a Service Account for Google Sheets, and an API Key for Gemini.

## 1. Google Sheets Authentication

We need a "Service Account" which is basically a robot user that your app uses to talk to Google Sheets securely.

### Step 1: Create a Project & Enable APIs
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or use an existing one).
3. In the search bar at the top, search for **"Google Sheets API"** and click **Enable**.
4. Search for **"Google Drive API"** and click **Enable**.

### Step 2: Create a Service Account
1. Go to the sidebar navigation (hamburger menu) -> **APIs & Services** -> **Credentials**.
2. Click **+ CREATE CREDENTIALS** at the top and select **Service account**.
3. Name it "Shopping App" and click **Create and Continue**, then **Done**.
4. You will see your new service account in the list. It will have an email address that looks like `shopping-app@your-project.iam.gserviceaccount.com`. **Copy this email address.**

### Step 3: Create the JSON Key
1. Click on the Service Account you just created.
2. Go to the **Keys** tab at the top.
3. Click **Add Key** -> **Create new key**.
4. Choose **JSON** and click **Create**. A file will download to your computer.
5. Move this file into the `shopping_app` folder and rename it exactly to **`service_account.json`**.

### Step 4: Share your Sheet
1. Open your "ShoppingList" Google Sheet in your browser.
2. Click the green **Share** button in the top right.
3. Paste the Service Account email address you copied earlier, give it **Editor** access, and click **Send**.

## 2. Google Gemini API Setup

We need a Gemini API key to read the product names from your photos.

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **Create API Key**.
3. Once generated, copy the key.
4. You can provide this key to the app in two ways:
   - **Option A:** Set it as an environment variable in your terminal before running the app: `export GEMINI_API_KEY="your-key-here"`
   - **Option B:** Open `shopping_app/main.py` and replace `'YOUR_GEMINI_API_KEY_HERE'` with your actual key on line 18.

## 3. Run the App

Once you have both the `service_account.json` file in the folder and your Gemini API key set:

1. Open a terminal and navigate to the folder:
   `cd "/Users/sarel/Library/CloudStorage/GoogleDrive-sareljf@gmail.com/My Drive/AntiGravity/shopping_app"`
2. Run the application:
   `python3 main.py`
3. Open your browser to `http://127.0.0.1:5001`.

To view it on your phone, you will need to find your Mac's local IP address (e.g., `192.168.1.X`) and open `http://192.168.1.X:5001` on your iPhone while connected to the same Wi-Fi.
