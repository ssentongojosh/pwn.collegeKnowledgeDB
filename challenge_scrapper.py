import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from dotenv import load_dotenv
from time import sleep
from notion_client import Client

# Load environment variables from .env file
load_dotenv()

# Define the core dojos
core_dojos = [
    "intro-to-cybersecurity",
    "program-security",
    "system-security",
    "software-exploitation"
]

# Base URL and login credentials
base_url = "https://pwn.college"
login_url = f"{base_url}/login"
session = requests.Session()

# Log in (credentials loaded from environment variables)
username = os.getenv("PWN_USERNAME")
password = os.getenv("PWN_PASSWORD")

# Notion API setup
notion_token = os.getenv("NOTION_TOKEN", "your_notion_token")
notion_page_id = os.getenv("NOTION_PAGE_ID", "your_parent_page_id")
notion = Client(auth=notion_token)

if not username or not password:
    print("Error: PWN_USERNAME and PWN_PASSWORD must be set in .env file")
    exit(1)

# First, get the login page to extract the nonce (CSRF token)
try:
    login_page_response = session.get(login_url)
    if login_page_response.status_code != 200:
        raise Exception("Failed to access login page.")
    
    # Parse the login page to extract the nonce
    soup = BeautifulSoup(login_page_response.content, "html.parser")
    nonce_input = soup.find("input", {"name": "nonce"})
    if not nonce_input:
        raise Exception("Could not find nonce token on login page.")
    
    nonce = nonce_input.get("value")
    
    # Prepare login data with correct field names and nonce
    login_data = {
        "name": username,  # Form uses 'name', not 'username'
        "password": password,
        "nonce": nonce,
        "_submit": "Submit"
    }
    
    # Attempt login
    response = session.post(login_url, data=login_data)
    
    # Check if login was successful (pwn.college typically redirects on successful login)
    if response.status_code == 200 and "login" in response.url.lower():
        raise Exception("Login failed. Check credentials.")
    elif response.status_code not in [200, 302]:
        raise Exception(f"Login failed with status code: {response.status_code}")
    
    print("Login successful!")
    
except Exception as e:
    print(f"Error during login: {e}")
    exit(1)

# Function to extract modules from a dojo page
def get_modules(dojo_name):
    dojo_url = f"{base_url}/{dojo_name}/"
    try:
        response = session.get(dojo_url)
        if response.status_code != 200:
            print(f"  ❌ Failed to access {dojo_url} (Status: {response.status_code})")
            return []
        soup = BeautifulSoup(response.content, "html.parser")
        modules = []
        for a in soup.find_all("a", href=lambda x: x and x.startswith(f"/{dojo_name}/")):
            module_name = a.text.strip()
            module_href = a["href"].split("/")[-2]  # Extract module slug
            
            # Extract progress information before cleaning
            import re
            users_solving = "0"
            progress_fraction = "0/0"
            progress_percentage = "0%"
            
            # Look for "X Hacking Y / Z" pattern
            hacking_match = re.search(r'(\d+)\s*hacking\s*(\d+)\s*/\s*(\d+)', module_name, re.IGNORECASE)
            if hacking_match:
                users_solving = hacking_match.group(1)
                completed = hacking_match.group(2)
                total = hacking_match.group(3)
                progress_fraction = f"{completed}/{total}"
            else:
                # Look for just "Y / Z" pattern
                fraction_match = re.search(r'(\d+)\s*/\s*(\d+)', module_name)
                if fraction_match:
                    completed = fraction_match.group(1)
                    total = fraction_match.group(2)
                    progress_fraction = f"{completed}/{total}"
            
            # Look for percentage pattern
            percentage_match = re.search(r'(\d+)%', module_name)
            if percentage_match:
                progress_percentage = f"{percentage_match.group(1)}%"
            
            # Clean the module name - remove progress info
            clean_module_name = module_name.split('\n')[0]
            clean_module_name = re.sub(r'\d+\s*hacking.*$', '', clean_module_name, flags=re.IGNORECASE).strip()
            clean_module_name = re.sub(r'\d+\s*/\s*\d+.*$', '', clean_module_name).strip()
            clean_module_name = re.sub(r'\d+%.*$', '', clean_module_name).strip()
            
            if clean_module_name:  # Only add if we have a valid module name
                modules.append((clean_module_name, module_href, users_solving, progress_fraction, progress_percentage))
        return modules
    except Exception as e:
        print(f"  ❌ Error accessing {dojo_url}: {e}")
        return []

# Function to extract challenges from a module page
def get_challenges(dojo_name, module_href):
    module_url = f"{base_url}/{dojo_name}/{module_href}/"
    try:
        response = session.get(module_url)
        if response.status_code != 200:
            print(f"        ❌ Failed to access {module_url} (Status: {response.status_code})")
            return []
        soup = BeautifulSoup(response.content, "html.parser")
        challenges = []
        for h4 in soup.find_all("h4", class_="accordion-item-name challenge-name"):
            span = h4.find("span", class_="pr-2")
            if span:
                challenge_name = span.text.strip()
                challenges.append(challenge_name)
        return challenges
    except Exception as e:
        print(f"        ❌ Error accessing {module_url}: {e}")
        return []

# Collect all data
data = []
print(f"\nStarting to scrape {len(core_dojos)} dojos...")
print("=" * 50)

for dojo_index, dojo in enumerate(core_dojos, 1):
    print(f"\n[{dojo_index}/{len(core_dojos)}] Processing dojo: {dojo}")
    print(f"URL: {base_url}/{dojo}/")
    
    modules = get_modules(dojo)
    if not modules:
        print(f"  ⚠️  No modules found for {dojo}")
        continue
    
    print(f"  ✓ Found {len(modules)} modules")
    
    for module_index, (module_name, module_href, users_solving, progress_fraction, progress_percentage) in enumerate(modules, 1):
        print(f"    [{module_index}/{len(modules)}] Module: {module_name}")
        
        challenges = get_challenges(dojo, module_href)
        if challenges:
            print(f"      ✓ Found {len(challenges)} challenges: {', '.join(challenges[:3])}" + 
                  ("..." if len(challenges) > 3 else ""))
            print(f"      📈 Progress: {progress_percentage} ({progress_fraction}) | {users_solving} users solving")
            
            data.append({
                "Dojo": dojo.replace("-", " ").title(),
                "Module": module_name,
                "Challenges": ", ".join(challenges),
                "Users Currently Solving": users_solving,
                "Progress Fraction": progress_fraction,
                "Progress Percentage": progress_percentage
            })
        else:
            print(f"      ⚠️  No challenges found in {module_name}")

print(f"\n" + "=" * 50)
print(f"Scraping complete! Collected data from {len(data)} modules total.")

# Convert to DataFrame and sort
print("\nProcessing data...")
df = pd.DataFrame(data)

# Filter out progress rows and extract progress information
print("Processing extracted data...")
print(f"Total rows to process: {len(df)}")

# Since we now extract progress info during module extraction, just process directly
processed_data = []
for _, row in df.iterrows():
    module_data = {
        "Dojo": row['Dojo'],
        "Module": row['Module'],
        "Challenges": row['Challenges'],
        "Users Currently Solving": row['Users Currently Solving'],
        "Progress Fraction": row['Progress Fraction'],
        "Progress Percentage": row['Progress Percentage']
    }
    processed_data.append(module_data)

# Create new DataFrame with processed data
df_processed = pd.DataFrame(processed_data)
df_processed = df_processed.sort_values(by=["Dojo", "Module"])

# Reorder columns for better readability
column_order = ["Dojo", "Module", "Progress Percentage", "Progress Fraction", "Users Currently Solving", "Challenges"]
df_processed = df_processed[column_order]

# Output as Markdown
print("Generating markdown table...")
markdown_table = df_processed.to_markdown(index=False)

# Save to file
print("Saving to file...")
with open("pwn_college_structure.md", "w") as f:
    f.write(markdown_table)
    
    
# Create Notion database
def create_notion_database(parent_page_id):
    try:
        database = notion.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": "pwn.college Core Materials Structure"}}],
            properties={
                "Dojo": {"title": {}},
                "Module": {"rich_text": {}},
                "Progress Percentage": {"rich_text": {}},
                "Progress Fraction": {"rich_text": {}},
                "Users Currently Solving": {"number": {}},
                "Challenges": {"rich_text": {}}
            }
        )
        return database["id"]
    except Exception as e:
        print(f"Error creating Notion database: {e}")
        exit(1)

# Add data to Notion database
def add_to_notion_database(database_id, data):
    for row in data:
        try:
            # Convert users_solving to integer for number field
            users_solving_num = int(row["Users Currently Solving"]) if row["Users Currently Solving"].isdigit() else 0
            
            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Dojo": {"title": [{"text": {"content": row["Dojo"]}}]},
                    "Module": {"rich_text": [{"text": {"content": row["Module"]}}]},
                    "Progress Percentage": {"rich_text": [{"text": {"content": row["Progress Percentage"]}}]},
                    "Progress Fraction": {"rich_text": [{"text": {"content": row["Progress Fraction"]}}]},
                    "Users Currently Solving": {"number": users_solving_num},
                    "Challenges": {"rich_text": [{"text": {"content": row["Challenges"]}}]}
                }
            )
            sleep(0.3)  # Rate limit: Notion API allows ~3 requests per second
        except Exception as e:
            print(f"Error adding row to Notion: {row['Module']}, {e}")

# Create and populate Notion database
try:
    database_id = create_notion_database(notion_page_id)
    add_to_notion_database(database_id, data)
    print(f"Scraping and Notion database creation complete. ")
    print("Markdown backup saved to 'pwn_college_structure.md'")
except Exception as e:
    print(f"Error with Notion integration: {e}")
    print("Markdown backup saved to 'pwn_college_structure.md'")
    

print(f"\n🎉 Scraping complete! Results saved to 'pwn_college_structure.md'")
print(f"📊 Total entries: {len(df_processed)} modules across {len(df_processed['Dojo'].unique())} dojos")