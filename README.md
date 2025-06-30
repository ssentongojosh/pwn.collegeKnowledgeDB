# pwn.college Challenge Scraper & Notion Integration

A Python tool that scrapes challenge data from pwn.college's core dojos and automatically creates organized Notion databases for tracking your cybersecurity learning progress.

## 🎯 What This Tool Does

This scraper automatically:
- **Extracts** challenge information from pwn.college's core dojos (Intro to Cybersecurity, Program Security, System Security, Software Exploitation)
- **Collects** challenge names, descriptions, progress data, and module organization
- **Creates** structured Notion databases for tracking your progress
- **Generates** individual challenge note templates with sections for analysis, solutions, flags, and learnings
- **Outputs** a markdown summary file for quick reference

## 📋 Features

- ✅ **Comprehensive Data Collection**: Scrapes all challenges from core dojos with descriptions
- ✅ **Notion Integration**: Creates two databases - main structure overview and detailed challenge notes
- ✅ **Progress Tracking**: Captures current solving statistics and completion percentages
- ✅ **Template Generation**: Pre-built note templates for each challenge with structured sections
- ✅ **Error Handling**: Robust handling of Notion API limitations and edge cases
- ✅ **Rate Limiting**: Respects both pwn.college and Notion API rate limits
- ✅ **Markdown Export**: Creates a local markdown file for offline reference

## 🛠️ Prerequisites

- Python 3.7+
- A pwn.college account with access to core dojos
- A Notion account with API access

## 📦 Installation

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd pwn.college
   ```

2. **Install required dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Environment Setup

### Step 1: Create Environment File

Create a `.env` file in the project root directory:

```bash
# Copy the example file and edit it
cp .env.example .env
# On Windows PowerShell: Copy-Item .env.example .env
```

### Step 2: Configure pwn.college Credentials

Add your pwn.college login credentials to the `.env` file:

```bash
# pwn.college Authentication
PWN_USERNAME=your_username_here
PWN_PASSWORD=your_password_here
```

**Important**: Make sure you have access to the core dojos on pwn.college. The script targets:
- `intro-to-cybersecurity`
- `program-security` 
- `system-security`
- `software-exploitation`

### Step 3: Set Up Notion Integration

#### 3.1 Create a Notion Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Name it (e.g., "pwn.college Scraper")
4. Select your workspace
5. Copy the **Internal Integration Token** (starts with `secret_`)

#### 3.2 Create a Parent Page in Notion

1. Create a new page in Notion where you want the databases
2. Copy the page ID from the URL:
   ```
   https://www.notion.so/Your-Page-Title-1234567890abcdef1234567890abcdef
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                            This is your page ID
   ```

#### 3.3 Share the Page with Your Integration

1. Open your parent page in Notion
2. Click **"Share"** in the top right
3. Click **"Invite"** and search for your integration name
4. Give it **"Can edit"** permissions

#### 3.4 Add Notion Credentials to .env

Add these lines to your `.env` file:

```bash
# Notion Integration
NOTION_TOKEN=secret_your_integration_token_here
NOTION_PAGE_ID=your_parent_page_id_here
```

### Complete .env File Example

Your final `.env` file should look like this:

```bash
# pwn.college Authentication
PWN_USERNAME=your_pwn_username
PWN_PASSWORD=your_pwn_password

# Notion Integration  
NOTION_TOKEN=secret_abcd1234567890abcdef1234567890abcdef12
NOTION_PAGE_ID=1234567890abcdef1234567890abcdef
```

## 🚀 Usage

Once your environment is configured, simply run:

```bash
python challenge_scrapper.py
```

### What Happens Next

The script will:

1. **Login** to pwn.college using your credentials
2. **Scrape** all core dojos for challenge data
3. **Create** two Notion databases:
   - **"pwn.college Core Materials Structure"** - Overview of all modules and challenges
   - **"pwn.college Challenge Notes"** - Individual challenge note templates
4. **Generate** a local `pwn_college_structure.md` file
5. **Display** progress and statistics in the terminal

## 📊 Output Structure

### Notion Databases Created

#### 1. Main Structure Database
- **Dojo**: The cybersecurity domain
- **Module**: Specific learning module  
- **Progress Percentage**: Current completion rate
- **Users Currently Solving**: Active solver count
- **Challenges**: Clickable links to individual challenge notes

#### 2. Challenge Notes Database
Each challenge gets a structured template with:
- **Challenge metadata** (dojo, module, status, difficulty)
- **📝 Challenge Description** (extracted from pwn.college)
- **🎯 Objective** section
- **🔍 Analysis & Approach** section
- **💻 Solution** section with code blocks
- **🚩 Flag** section
- **📚 Key Learnings** section
- **🔗 References** section

### Local Markdown File
A `pwn_college_structure.md` file is created with a table view of all modules and challenges.

## 🔧 Troubleshooting

### Common Issues

#### Authentication Errors

```text
Error during login: Login failed. Check credentials.
```

- Verify your pwn.college credentials are correct in `.env`
- Ensure you have access to core dojos
- Check that your account isn't locked or requires 2FA

#### Notion API Errors

```text
Error creating Notion database: Unauthorized (401)
```

- Verify your integration token is correct (starts with `secret_`)
- Ensure the parent page is shared with your integration
- Check that the page ID is copied correctly (32 characters, no hyphens)

```text
Error creating template for challenge: invalid_url
```

- This is automatically handled by URL sanitization
- May indicate temporary network issues - script will continue

#### Rate Limiting

```text
❌ Error creating template for challenge: rate limit
```

- The script includes built-in delays (0.5s between Notion API calls)
- If you hit rate limits, wait a few minutes and retry
- Consider increasing delays in the code for slower execution

#### Missing Dependencies

```bash
pip install --upgrade requests beautifulsoup4 pandas python-dotenv notion-client
```

### Environment Variable Verification

Test your setup with this quick check:

```python
import os
from dotenv import load_dotenv

load_dotenv()
print("PWN_USERNAME:", "✓" if os.getenv("PWN_USERNAME") else "❌")
print("PWN_PASSWORD:", "✓" if os.getenv("PWN_PASSWORD") else "❌") 
print("NOTION_TOKEN:", "✓" if os.getenv("NOTION_TOKEN") else "❌")
print("NOTION_PAGE_ID:", "✓" if os.getenv("NOTION_PAGE_ID") else "❌")
```

### Debug Mode

The script includes comprehensive error reporting. Look for:

- ✅ Success indicators for each operation
- ❌ Error messages with specific failure reasons
- Progress statistics and summary at the end

For additional debugging, check:

- The generated `pwn_college_structure.md` file
- Notion databases for partial completion
- Console output for specific error patterns

## 📝 Notes

- The script respects rate limits for both pwn.college and Notion APIs
- Challenge descriptions are converted from HTML to Notion-compatible blocks
- All URLs and code block languages are sanitized for Notion compatibility
- Progress data reflects real-time statistics from pwn.college

## 🔒 Security

- Keep your `.env` file secure and never commit it to version control
- Consider using environment variables directly in production environments
- Your Notion integration only has access to pages you explicitly share with it

## 🤝 Contributing

Feel free to submit issues, feature requests, or improvements to enhance the scraper's functionality.

## 📄 License

This project is provided as-is for educational purposes. Please respect pwn.college's terms of service and rate limits when using this tool.
