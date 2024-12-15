# Cash Custody Manager

## Overview
Cash Custody Manager is a personal finance tracking application that helps you manage your expenses, accounts, and transactions efficiently.

## Running the Application

### Option 1: Executable
1. Navigate to the `dist/CashCustodyManager` folder
2. Double-click `CashCustodyManager.exe` to run the application
3. The app will open in your default web browser at `http://127.0.0.1:5001`

### Option 2: Python Script
1. Ensure you have Python 3.7+ installed
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python simple_app.py`

## Features
- Create and manage multiple accounts
- Track expenses, deposits, and transfers
- Upload and manage transaction receipts
- Export transaction data to Excel
- Simple and intuitive user interface

## Data Storage
- Accounts and transactions are stored in Excel files in the `data/` directory
- Receipts are saved in the `uploads/` directory

## Troubleshooting
- Ensure you have write permissions in the application directory
- Check that all required dependencies are installed
- If you encounter any issues, please create an issue on the project repository

## Antivirus Compatibility

### Potential False Positive Detection
Some antivirus software might flag the executable as suspicious due to it being a PyInstaller-generated application. This is a common occurrence with Python-packaged executables.

### Recommended Steps
1. If your antivirus blocks the application:
   - Add an exception for the executable
   - Temporarily disable real-time protection to verify the application
   - Submit the file to your antivirus vendor for analysis

2. Verify the application's integrity:
   - Check the digital signature (coming soon)
   - Scan the executable with multiple antivirus engines
   - Run the executable in a sandboxed environment first

### Why Might Antivirus Detect This?
- PyInstaller packages create compressed, self-extracting executables
- The packaging process can resemble behavior of some malware
- No embedded digital signature (which is normal for small applications)

### Transparency
- Source code is available for review
- All dependencies are open-source
- Application runs locally with no external connections

## License
[Your License Here]

## Contact
[Your Contact Information]
