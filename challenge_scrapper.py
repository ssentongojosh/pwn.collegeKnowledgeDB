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
login_data = {
    "username": username,
    "password": password
}
try:
    response = session.post(login_url, data=login_data)
    if response.status_code != 200:
        raise Exception("Login failed. Check credentials or website status.")
except Exception as e:
    print(f"Error during login: {e}")
    exit(1)

# Function to extract modules from a dojo page
def get_modules(dojo_name):
    dojo_url = f"{base_url}/{dojo_name}/"
    try:
        response = session.get(dojo_url)
        if response.status_code != 200:
            print(f"Failed to access {dojo_url}. Skipping...")
            return []
        soup = BeautifulSoup(response.content, "html.parser")
        modules = []
        for a in soup.find_all("a", href=lambda x: x and x.startswith(f"/{dojo_name}/")):
            module_name = a.text.strip()
            module_href = a["href"].split("/")[-2]  # Extract module slug
            modules.append((module_name, module_href))
        return modules
    except Exception as e:
        print(f"Error accessing {dojo_url}: {e}")
        return []

# Function to extract challenges from a module page
def get_challenges(dojo_name, module_href):
    module_url = f"{base_url}/{dojo_name}/{module_href}/"
    try:
        response = session.get(module_url)
        if response.status_code != 200:
            print(f"Failed to access {module_url}. Skipping...")
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
        print(f"Error accessing {module_url}: {e}")
        return []

# Collect all data
data = []
for dojo in core_dojos:
    modules = get_modules(dojo)
    for module_name, module_href in modules:
        challenges = get_challenges(dojo, module_href)
        if challenges:
            data.append({
                "Dojo": dojo.replace("-", " ").title(),
                "Module": module_name,
                "Challenges": ", ".join(challenges)
            })

# Convert to DataFrame and sort
df = pd.DataFrame(data)
df = df.sort_values(by=["Dojo", "Module", "Challenges"])

# Output as Markdown
markdown_table = df.to_markdown(index=False)

# Save to file
with open("pwn_college_structure.md", "w") as f:
    f.write(markdown_table)

print("Scraping complete. Results saved to 'pwn_college_structure.md'")