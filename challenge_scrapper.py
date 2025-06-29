import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from dotenv import load_dotenv

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
            modules.append((module_name, module_href))
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
    
    for module_index, (module_name, module_href) in enumerate(modules, 1):
        print(f"    [{module_index}/{len(modules)}] Module: {module_name}")
        
        challenges = get_challenges(dojo, module_href)
        if challenges:
            print(f"      ✓ Found {len(challenges)} challenges: {', '.join(challenges[:3])}" + 
                  ("..." if len(challenges) > 3 else ""))
            data.append({
                "Dojo": dojo.replace("-", " ").title(),
                "Module": module_name,
                "Challenges": ", ".join(challenges)
            })
        else:
            print(f"      ⚠️  No challenges found in {module_name}")

print(f"\n" + "=" * 50)
print(f"Scraping complete! Collected data from {len(data)} modules total.")

# Convert to DataFrame and sort
print("\nProcessing data...")
df = pd.DataFrame(data)
df = df.sort_values(by=["Dojo", "Module", "Challenges"])

# Output as Markdown
print("Generating markdown table...")
markdown_table = df.to_markdown(index=False)

# Save to file
print("Saving to file...")
with open("pwn_college_structure.md", "w") as f:
    f.write(markdown_table)

print(f"\n🎉 Scraping complete! Results saved to 'pwn_college_structure.md'")
print(f"📊 Total entries: {len(df)} modules across {len(df['Dojo'].unique())} dojos")