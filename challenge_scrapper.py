import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from dotenv import load_dotenv
from time import sleep
from notion_client import Client
import urllib.parse



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
                "Challenges": ", ".join([f"`{challenge}`" for challenge in challenges]),
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
    
    
# Function to create a challenge note template
def create_challenge_template(dojo_name, module_name, challenge_name):
    """Create a structured template for challenge notes"""
    try:
        # Create the page with a structured template
        page = notion.pages.create(
            parent={"page_id": notion_page_id},
            properties={
                "title": [{"text": {"content": f"{dojo_name} - {module_name} - {challenge_name}"}}]
            },
            children=[
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"text": {"content": f"Challenge: {challenge_name}"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"text": {"content": "Dojo: "}, "annotations": {"bold": True}},
                            {"text": {"content": dojo_name}}
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"text": {"content": "Module: "}, "annotations": {"bold": True}},
                            {"text": {"content": module_name}}
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"text": {"content": "Challenge URL: "}, "annotations": {"bold": True}},
                            {"text": {"content": f"https://pwn.college/{dojo_name.lower().replace(' ', '-')}/{module_name.lower().replace(' ', '-')}/"}, "annotations": {"code": True}}
                        ]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "📝 Challenge Description"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": "Write the challenge description here..."}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🎯 Objective"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": "What is the goal of this challenge?"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🔍 Analysis & Approach"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Initial analysis and observations"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Tools and techniques used"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Strategy and methodology"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "💻 Solution"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": "# Add your solution code here\n# Commands, scripts, or exploits used\n"}}],
                        "language": "bash"
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🚩 Flag"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": "flag{your_flag_here}"}}],
                        "language": "plain text"
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "📚 Key Learnings"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "What did you learn from this challenge?"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Key concepts or techniques"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Pitfalls to avoid"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🔗 References"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Links to helpful resources"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Documentation and tutorials"}}]
                    }
                }
            ]
        )
        return page["url"]
    except Exception as e:
        print(f"Error creating template for {challenge_name}: {e}")
        # Fallback to simple new page URL
        note_title = f"{dojo_name} - {module_name} - {challenge_name}"
        return f"https://www.notion.so/new?title={note_title.replace(' ', '%20')}"

# Function to create a challenge notes database
def create_challenge_notes_database(parent_page_id):
    """Create a database for challenge notes with a template structure"""
    try:
        database = notion.databases.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": "pwn.college Challenge Notes"}}],
            properties={
                "Challenge": {"title": {}},
                "Dojo": {"select": {"options": [
                    {"name": "Intro To Cybersecurity", "color": "blue"},
                    {"name": "Program Security", "color": "green"},
                    {"name": "System Security", "color": "yellow"},
                    {"name": "Software Exploitation", "color": "red"}
                ]}},
                "Module": {"rich_text": {}},
                "Status": {"select": {"options": [
                    {"name": "Not Started", "color": "gray"},
                    {"name": "In Progress", "color": "yellow"},
                    {"name": "Completed", "color": "green"},
                    {"name": "Stuck", "color": "red"}
                ]}},
                "Difficulty": {"select": {"options": [
                    {"name": "Easy", "color": "green"},
                    {"name": "Medium", "color": "yellow"},
                    {"name": "Hard", "color": "red"}
                ]}},
                "Flag": {"rich_text": {}},
                "URL": {"url": {}},
                "Date Completed": {"date": {}},
                "Tags": {"multi_select": {"options": [
                    {"name": "Binary Exploitation", "color": "red"},
                    {"name": "Web Security", "color": "blue"},
                    {"name": "Cryptography", "color": "purple"},
                    {"name": "Reverse Engineering", "color": "orange"},
                    {"name": "System Exploitation", "color": "yellow"}
                ]}}
            }
        )
        
        # Create a template page within the database
        template_page = notion.pages.create(
            parent={"database_id": database["id"]},
            properties={
                "Challenge": {"title": [{"text": {"content": "Template - Challenge Name"}}]},
                "Dojo": {"select": {"name": "Intro To Cybersecurity"}},
                "Module": {"rich_text": [{"text": {"content": "Module Name"}}]},
                "Status": {"select": {"name": "Not Started"}},
                "URL": {"url": "https://pwn.college/"}
            },
            children=[
                {
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"text": {"content": "Challenge Template"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"text": {"content": "This is a template page. Copy this structure for your challenge notes!"}}],
                        "icon": {"emoji": "📝"}
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "📝 Challenge Description"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": "Write the challenge description here..."}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🎯 Objective"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": "What is the goal of this challenge?"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🔍 Analysis & Approach"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Initial analysis and observations"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Tools and techniques used"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Strategy and methodology"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "💻 Solution"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": "# Add your solution code here\n# Commands, scripts, or exploits used\n"}}],
                        "language": "bash"
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🚩 Flag"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"text": {"content": "flag{your_flag_here}"}}],
                        "language": "plain text"
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "📚 Key Learnings"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "What did you learn from this challenge?"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Key concepts or techniques"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Pitfalls to avoid"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🔗 References"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Links to helpful resources"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"text": {"content": "Documentation and tutorials"}}]
                    }
                }
            ]
        )
        
        return database["id"]
    except Exception as e:
        print(f"Error creating challenge notes database: {e}")
        return None

# Function to format challenges for Notion with clickable links
def format_challenges_for_notion(challenges, dojo_name, module_name):
    """Convert list of challenges to Notion rich text with clickable links to note templates"""
    rich_text_parts = []
    
    for i, challenge in enumerate(challenges):
        if i > 0:
            # Add comma and space between challenges
            rich_text_parts.append({"type": "text", "text": {"content": ", "}})
        
        # For now, just make them code-formatted without links until we create the database
        rich_text_parts.append({
            "type": "text", 
            "text": {"content": challenge},
            "annotations": {"code": True}
        })
    
    return rich_text_parts

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
            
            # Parse challenges from the comma-separated backtick format
            challenges_text = row["Challenges"]
            challenges_list = []
            if challenges_text:
                # Remove backticks and split by comma
                challenges_list = [challenge.strip().strip('`') for challenge in challenges_text.split(',')]
            
            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Dojo": {"title": [{"text": {"content": row["Dojo"]}}]},
                    "Module": {"rich_text": [{"text": {"content": row["Module"]}}]},
                    "Progress Percentage": {"rich_text": [{"text": {"content": row["Progress Percentage"]}}]},
                    "Progress Fraction": {"rich_text": [{"text": {"content": row["Progress Fraction"]}}]},
                    "Users Currently Solving": {"number": users_solving_num},
                    "Challenges": {"rich_text": format_challenges_for_notion(challenges_list, row["Dojo"], row["Module"])}
                }
            )
            sleep(0.3)  # Rate limit: Notion API allows ~3 requests per second
        except Exception as e:
            print(f"Error adding row to Notion: {row['Module']}, {e}")

# Create and populate Notion database
try:
    print("Creating main structure database...")
    database_id = create_notion_database(notion_page_id)
    
    print("Creating challenge notes database...")
    challenge_notes_db_id = create_challenge_notes_database(notion_page_id)
    
    if challenge_notes_db_id:
        print("Updating challenge links to point to notes database...")
        # Now update the format function to use the database ID
        def format_challenges_with_links(challenges, dojo_name, module_name):
            rich_text_parts = []
            for i, challenge in enumerate(challenges):
                if i > 0:
                    rich_text_parts.append({"type": "text", "text": {"content": ", "}})
                
                # Create a pre-filled template page for each challenge
                try:
                    # Create a dedicated page for this specific challenge
                    template_page = notion.pages.create(
                        parent={"database_id": challenge_notes_db_id},
                        properties={
                            "Challenge": {"title": [{"text": {"content": challenge}}]},
                            "Dojo": {"select": {"name": dojo_name}},
                            "Module": {"rich_text": [{"text": {"content": module_name}}]},
                            "Status": {"select": {"name": "Not Started"}},
                            "URL": {"url": f"https://pwn.college/{dojo_name.lower().replace(' ', '-')}/"}
                        },
                        children=[
                            {
                                "object": "block",
                                "type": "heading_1",
                                "heading_1": {
                                    "rich_text": [{"text": {"content": f"Challenge: {challenge}"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {"text": {"content": "Dojo: "}, "annotations": {"bold": True}},
                                        {"text": {"content": dojo_name}}
                                    ]
                                }
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {"text": {"content": "Module: "}, "annotations": {"bold": True}},
                                        {"text": {"content": module_name}}
                                    ]
                                }
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [
                                        {"text": {"content": "Challenge URL: "}, "annotations": {"bold": True}},
                                        {"text": {"content": f"https://pwn.college/{dojo_name.lower().replace(' ', '-')}/"}, "annotations": {"code": True}}
                                    ]
                                }
                            },
                            {
                                "object": "block",
                                "type": "divider",
                                "divider": {}
                            },
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"text": {"content": "📝 Challenge Description"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"text": {"content": "Write the challenge description here..."}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"text": {"content": "🎯 Objective"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"text": {"content": "What is the goal of this challenge?"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"text": {"content": "🔍 Analysis & Approach"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "Initial analysis and observations"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "Tools and techniques used"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "Strategy and methodology"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"text": {"content": "💻 Solution"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "code",
                                "code": {
                                    "rich_text": [{"text": {"content": "# Add your solution code here\n# Commands, scripts, or exploits used\n"}}],
                                    "language": "bash"
                                }
                            },
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"text": {"content": "🚩 Flag"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "code",
                                "code": {
                                    "rich_text": [{"text": {"content": "flag{your_flag_here}"}}],
                                    "language": "plain text"
                                }
                            },
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"text": {"content": "📚 Key Learnings"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "What did you learn from this challenge?"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "Key concepts or techniques"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "Pitfalls to avoid"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {
                                    "rich_text": [{"text": {"content": "🔗 References"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "Links to helpful resources"}}]
                                }
                            },
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"text": {"content": "Documentation and tutorials"}}]
                                }
                            }
                        ]
                    )
                    
                    page_url = template_page["url"]
                    sleep(0.1)  # Small delay to avoid rate limiting
                    
                except Exception as e:
                    print(f"Warning: Could not create template for {challenge}: {e}")
                    # Fallback to generic database URL
                    page_url = f"https://www.notion.so/{challenge_notes_db_id.replace('-', '')}?p=new"
                
                rich_text_parts.append({
                    "type": "text", 
                    "text": {"content": challenge, "link": {"url": page_url}},
                    "annotations": {"code": True}
                })
            return rich_text_parts
        
        # Update the processed data with clickable links
        for row in processed_data:
            challenges_text = row["Challenges"]
            if challenges_text:
                challenges_list = [challenge.strip().strip('`') for challenge in challenges_text.split(',')]
                row["Challenges_Rich"] = format_challenges_with_links(challenges_list, row["Dojo"], row["Module"])
    
    print("Adding challenge data to main database...")
    for row in processed_data:
        try:
            users_solving_num = int(row["Users Currently Solving"]) if row["Users Currently Solving"].isdigit() else 0
            
            # Use clickable links if available, otherwise use original format
            if challenge_notes_db_id and "Challenges_Rich" in row:
                challenges_rich_text = row["Challenges_Rich"]
            else:
                challenges_text = row["Challenges"]
                challenges_list = []
                if challenges_text:
                    challenges_list = [challenge.strip().strip('`') for challenge in challenges_text.split(',')]
                challenges_rich_text = format_challenges_for_notion(challenges_list, row["Dojo"], row["Module"])
            
            notion.pages.create(
                parent={"database_id": database_id},
                properties={
                    "Dojo": {"title": [{"text": {"content": row["Dojo"]}}]},
                    "Module": {"rich_text": [{"text": {"content": row["Module"]}}]},
                    "Progress Percentage": {"rich_text": [{"text": {"content": row["Progress Percentage"]}}]},
                    "Progress Fraction": {"rich_text": [{"text": {"content": row["Progress Fraction"]}}]},
                    "Users Currently Solving": {"number": users_solving_num},
                    "Challenges": {"rich_text": challenges_rich_text}
                }
            )
            sleep(0.3)  # Rate limit
        except Exception as e:
            print(f"Error adding row to Notion: {row['Module']}, {e}")
    
    print(f"✅ Scraping and Notion database creation complete!")
    print(f"📊 Created main database with {len(processed_data)} modules")
    if challenge_notes_db_id:
        print(f"📝 Created challenge notes database with template")
        print(f"🔗 Each challenge name is now clickable and will link to a PRE-FILLED note!")
        print("💡 What happens when you click a challenge name:")
        print("   ✓ Opens a dedicated page for that specific challenge")
        print("   ✓ Pre-filled with challenge name, dojo, and module")
        print("   ✓ Includes structured template for notes")
        print("   ✓ Ready for you to add your solution and learnings!")
    print("Markdown backup saved to 'pwn_college_structure.md'")
except Exception as e:
    print(f"Error with Notion integration: {e}")
    print("Markdown backup saved to 'pwn_college_structure.md'")
    




print(f"\n🎉 Scraping complete! Results saved to 'pwn_college_structure.md'")
print(f"📊 Total entries: {len(df_processed)} modules across {len(df_processed['Dojo'].unique())} dojos")