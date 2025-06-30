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
                
                # Extract challenge description if available
                description = None
                desc_div = h4.find_next("div", class_="challenge-description")
                if desc_div:
                    description = desc_div  # Pass the actual HTML element
                
                challenges.append((challenge_name, description))
        return challenges
    except Exception as e:
        print(f"        ❌ Error accessing {module_url}: {e}")
        return []

# Function to safely truncate content for Notion limits
def safe_truncate_content(content, max_length=2000):
    """Truncate content to fit Notion API limits while preserving readability"""
    if not content or len(content) <= max_length:
        return content
    
    # Find a good place to truncate (at word boundary)
    truncated = content[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  # If we can find a reasonable word boundary
        truncated = truncated[:last_space]
    
    return truncated + "... [content truncated]"

# Function to sanitize URLs for Notion
def sanitize_url(url):
    """Sanitize URLs to ensure they are valid for Notion"""
    if not url or not isinstance(url, str):
        return None
    
    # Remove any leading/trailing whitespace
    url = url.strip()
    
    # If URL doesn't start with http/https, try to make it valid
    if not url.startswith(('http://', 'https://')):
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = 'https://pwn.college' + url
        elif '.' in url and not url.startswith('mailto:'):
            url = 'https://' + url
        else:
            # If we can't make it a valid URL, return None
            return None
    
    # Basic URL validation - check if it looks like a valid URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return url
        else:
            return None
    except:
        return None

# Function to get safe language for Notion code blocks
def get_safe_notion_language(language):
    """Convert language to a Notion-supported code language"""
    if not language:
        return "text"
    
    # Notion supported languages (as of 2024)
    notion_languages = {
        "abap", "agda", "arduino", "assembly", "bash", "basic", "bnf", "c", "c#", "c++", 
        "clojure", "coffeescript", "coq", "css", "dart", "dhall", "diff", "docker", 
        "ebnf", "elixir", "elm", "erlang", "f#", "flow", "fortran", "gherkin", "glsl", 
        "go", "graphql", "groovy", "haskell", "html", "idris", "java", "javascript", 
        "json", "julia", "kotlin", "latex", "less", "lisp", "livescript", "llvm ir", 
        "lua", "makefile", "markdown", "markup", "matlab", "mathematica", "mermaid", 
        "nix", "notion formula", "objective-c", "ocaml", "pascal", "perl", "php", 
        "plain text", "powershell", "prolog", "protobuf", "purescript", "python", 
        "r", "racket", "reason", "ruby", "rust", "sass", "scala", "scheme", "scss", 
        "shell", "solidity", "sql", "swift", "toml", "typescript", "vb.net", 
        "verilog", "vhdl", "visual basic", "webassembly", "xml", "yaml", "zig"
    }
    
    # Normalize the input language
    lang = language.lower().strip()
    
    # Direct mapping for common cases
    language_mapping = {
        "sh": "bash",
        "shell": "bash", 
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "cpp": "c++",
        "csharp": "c#",
        "cs": "c#",
        "fsharp": "f#",
        "fs": "f#",
        "yml": "yaml",
        "text": "plain text",
        "txt": "plain text",
        "plaintext": "plain text",
        "console": "bash",
        "terminal": "bash",
        "cmd": "bash",
        "powershell": "powershell",
        "ps1": "powershell"
    }
    
    # Check direct mapping first
    if lang in language_mapping:
        return language_mapping[lang]
    
    # Check if it's already a valid Notion language
    if lang in notion_languages:
        return lang
    
    # For unknown languages, default to safe options based on common patterns
    if any(keyword in lang for keyword in ["script", "bash", "sh", "shell", "console", "terminal"]):
        return "bash"
    elif any(keyword in lang for keyword in ["python", "py"]):
        return "python"
    elif any(keyword in lang for keyword in ["javascript", "js", "node"]):
        return "javascript"
    elif any(keyword in lang for keyword in ["html", "web"]):
        return "html"
    elif any(keyword in lang for keyword in ["css", "style"]):
        return "css"
    elif any(keyword in lang for keyword in ["sql", "database"]):
        return "sql"
    elif any(keyword in lang for keyword in ["json"]):
        return "json"
    elif any(keyword in lang for keyword in ["xml"]):
        return "xml"
    elif any(keyword in lang for keyword in ["yaml", "yml"]):
        return "yaml"
    else:
        # Default fallback
        return "text"

# Function to convert HTML content to Notion blocks
def html_to_notion_blocks(html_content):
    """Converts HTML from a BeautifulSoup tag into a list of Notion blocks."""
    if not html_content:
        return [{
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": "No description provided."}}]}
        }]

    # If html_content is a string, convert it to a simple paragraph block
    if isinstance(html_content, str):
        if html_content.strip():
            return [{
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": html_content.strip()}}]}
            }]
        else:
            return [{
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": "No description provided."}}]}
            }]

    blocks = []
    # Process children of the main div to preserve structure
    for tag in html_content.find_all(True, recursive=False):
        if tag.name == 'p':
            # Handle paragraphs, including nested <a> and <code> tags
            rich_text = []
            for child in tag.children:
                if isinstance(child, str):
                    rich_text.append({"type": "text", "text": {"content": child}})
                elif child.name == 'a' and child.has_attr('href'):
                    # Sanitize the URL before adding
                    safe_url = sanitize_url(child['href'])
                    if safe_url:
                        rich_text.append({"type": "text", "text": {"content": child.get_text(), "link": {"url": safe_url}}})
                    else:
                        # If URL is invalid, just add as plain text
                        rich_text.append({"type": "text", "text": {"content": child.get_text()}})
                elif child.name == 'code':
                    rich_text.append({"type": "text", "text": {"content": child.get_text()}, "annotations": {"code": True}})
                else:
                    rich_text.append({"type": "text", "text": {"content": child.get_text()}})
            if rich_text:  # Only add if we have content
                blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": rich_text}})
        
        elif tag.name == 'pre' and tag.find('code'):
            # Handle code blocks with safe language detection
            code_text = tag.get_text()
            if code_text.strip():  # Only add if there's actual content
                language_class = tag.find('code').get('class', [])
                raw_language = language_class[0].replace('language-', '') if language_class else 'bash'
                safe_language = get_safe_notion_language(raw_language)
                
                blocks.append({
                    "object": "block", "type": "code",
                    "code": {"rich_text": [{"text": {"content": code_text}}], "language": safe_language}
                })
            
        elif tag.name in ['ul', 'ol']:
            # Handle lists
            for li in tag.find_all('li', recursive=False):
                list_text = li.get_text(strip=True)
                if list_text:  # Only add if there's content
                    blocks.append({
                        "object": "block", "type": "bulleted_list_item",
                        "bulleted_list_item": {"rich_text": [{"text": {"content": list_text}}]}
                    })
        
        elif tag.name.startswith('h'):
            # Handle headings
            heading_text = tag.get_text(strip=True)
            if heading_text:  # Only add if there's content
                try:
                    level = int(tag.name[1])
                    heading_type = f"heading_{level}" if level in [1, 2, 3] else "paragraph"
                    if heading_type != "paragraph":
                        blocks.append({
                            "object": "block", "type": heading_type,
                            heading_type: {"rich_text": [{"text": {"content": heading_text}}]}
                        })
                    else:
                         blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": heading_text}, "annotations": {"bold": True}}]}})
                except (ValueError, IndexError):
                    # Fallback for non-standard heading tags like h4, h5, etc.
                    blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": heading_text}, "annotations": {"bold": True}}]}})

        else:
            # Fallback for any other tags
            text = tag.get_text(strip=True)
            if text:
                blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": text}}]}})

    return blocks if blocks else [{
        "object": "block", "type": "paragraph",
        "paragraph": {"rich_text": [{"text": {"content": "Description available but could not be parsed."}}]}
    }]


# Collect all data
data = []
all_challenges = []
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
            challenge_names = [c[0] for c in challenges]
            print(f"      ✓ Found {len(challenges)} challenges: {', '.join(challenge_names[:3])}" + 
                  ("..." if len(challenge_names) > 3 else ""))
            print(f"      📈 Progress: {progress_percentage} ({progress_fraction}) | {users_solving} users solving")
            
            # Store data for markdown output (only challenge names)
            data.append({
                "Dojo": dojo.replace("-", " ").title(),
                "Module": module_name,
                "Challenges": ", ".join([f"`{challenge[0]}`" for challenge in challenges]),
                "Users Currently Solving": users_solving,
                "Progress Fraction": progress_fraction,
                "Progress Percentage": progress_percentage
            })
            
            # Store full challenge data for Notion creation
            for challenge_name, description_html in challenges:
                all_challenges.append({
                    "Dojo": dojo.replace("-", " ").title(),
                    "Module": module_name,
                    "Challenge": challenge_name,
                    "DescriptionHTML": description_html
                })
        else:
            print(f"      ⚠️  No challenges found in {module_name}")

print(f"\n" + "=" * 50)
print(f"Scraping complete! Collected data from {len(data)} modules, {len(all_challenges)} challenges total.")

# Convert to DataFrame and sort
print("\nProcessing data...")
df = pd.DataFrame(data)

# Process and sort the data
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
        return database["id"]
    except Exception as e:
        print(f"Error creating challenge notes database: {e}")
        return None

# Function to format challenges for Notion with clickable links
def format_challenges_for_notion(challenges, dojo_name, module_name, challenge_urls):
    """Convert list of challenges to Notion rich text with clickable links to note templates"""
    rich_text_parts = []
    
    for i, challenge in enumerate(challenges):
        if i > 0:
            # Add comma and space between challenges
            rich_text_parts.append({"type": "text", "text": {"content": ", "}})
        
        # Create clickable link to the challenge page
        challenge_url = challenge_urls.get(challenge, "")
        if challenge_url:
            rich_text_parts.append({
                "type": "text", 
                "text": {"content": challenge, "link": {"url": challenge_url}},
                "annotations": {"code": True}
            })
        else:
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
        return None

# Add data to Notion database
def add_to_notion_database(database_id, data, challenge_urls):
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
                    "Challenges": {"rich_text": format_challenges_for_notion(challenges_list, row["Dojo"], row["Module"], challenge_urls)}
                }
            )
            sleep(0.3)  # Rate limit: Notion API allows ~3 requests per second
        except Exception as e:
            print(f"Error adding row to Notion: {row['Module']}, {e}")


# Function to create a challenge note template
def create_challenge_template(dojo_name, module_name, challenge_name, description_html, database_id):
    """Create a structured template for challenge notes in the database"""
    
    # Convert description from HTML to Notion blocks
    description_blocks = html_to_notion_blocks(description_html)

    try:
        # Validate and sanitize the challenge URL
        challenge_url = f"https://pwn.college/{dojo_name.lower().replace(' ', '-')}/{module_name.lower().replace(' ', '-')}/"
        safe_challenge_url = sanitize_url(challenge_url)
        
        # Build properties with safe URL
        properties = {
            "Challenge": {"title": [{"text": {"content": challenge_name}}]},
            "Dojo": {"select": {"name": dojo_name}},
            "Module": {"rich_text": [{"text": {"content": module_name}}]},
            "Status": {"select": {"name": "Not Started"}}
        }
        
        # Only add URL if it's valid
        if safe_challenge_url:
            properties["URL"] = {"url": safe_challenge_url}
        
        # Create the page in the challenge notes database
        page = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=[
                {
                    "object": "block", "type": "heading_1",
                    "heading_1": {"rich_text": [{"text": {"content": f"Challenge: {challenge_name}"}}]}
                },
                {
                    "object": "block", "type": "paragraph",
                    "paragraph": { "rich_text": [
                        {"text": {"content": "Dojo: "}, "annotations": {"bold": True}},
                        {"text": {"content": dojo_name}}
                    ]}
                },
                {
                    "object": "block", "type": "paragraph",
                    "paragraph": { "rich_text": [
                        {"text": {"content": "Module: "}, "annotations": {"bold": True}},
                        {"text": {"content": module_name}}
                    ]}
                },
                {
                    "object": "block", "type": "divider", "divider": {}
                },
                {
                    "object": "block", "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": "📝 Challenge Description"}}]}
                },
                *description_blocks,  # Unpack the generated description blocks
                {
                    "object": "block", "type": "heading_2",
                    "heading_2": {"rich_text": [{"text": {"content": "🎯 Objective"}}]}
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
        # More detailed error handling
        error_msg = str(e)
        print(f"    ❌ Error creating template for {challenge_name}: {error_msg}")
        
        # Check for specific common errors
        if "invalid_url" in error_msg.lower():
            print(f"       → URL validation failed for challenge URL")
        elif "validation failed" in error_msg.lower():
            print(f"       → Notion validation failed - likely malformed content")
        elif "request timeout" in error_msg.lower():
            print(f"       → Request timeout - retrying might help")
        elif "rate limit" in error_msg.lower():
            print(f"       → Rate limited - please wait before retrying")
        else:
            print(f"       → Unexpected error: {error_msg}")
        
        return None

# Create and populate Notion databases
try:
    print("\nCreating challenge notes database...")
    challenge_notes_db_id = create_challenge_notes_database(notion_page_id)
    
    if not challenge_notes_db_id:
        print("❌ Failed to create challenge notes database. Exiting...")
        exit(1)
    
    print("✓ Challenge notes database created")
    
    print("\nCreating individual challenge pages in database...")
    print("=" * 50)
    
    # Create individual challenge pages in the database and collect their URLs
    challenge_urls = {}
    for i, challenge_data in enumerate(all_challenges, 1):
        print(f"[{i}/{len(all_challenges)}] Creating page for: {challenge_data['Challenge']}")
        try:
            page_url = create_challenge_template(
                dojo_name=challenge_data["Dojo"],
                module_name=challenge_data["Module"],
                challenge_name=challenge_data["Challenge"],
                description_html=challenge_data["DescriptionHTML"],
                database_id=challenge_notes_db_id
            )
            if page_url:
                challenge_urls[challenge_data["Challenge"]] = page_url
            sleep(0.5)  # Respect Notion API rate limits
        except Exception as e:
            print(f"  ❌ Failed to create Notion page for {challenge_data['Challenge']}: {e}")
    
    print(f"\n✓ Created {len(challenge_urls)} challenge pages in database")
    
    print("\nCreating main structure database...")
    database_id = create_notion_database(notion_page_id)
    
    if database_id:
        print("Adding data to main database with clickable challenge links...")
        add_to_notion_database(database_id, processed_data, challenge_urls)
        print("✓ Main database created and populated")

except Exception as e:
    print(f"Error in Notion setup: {e}")

print("\n" + "=" * 50)
print("All done! Created:")
print(f"- Markdown file: pwn_college_structure.md")
print(f"- Challenge notes database with {len(challenge_urls)} challenge entries")
print(f"- Main structure database with clickable challenge links")
print(f"- All challenges now organized in database format")