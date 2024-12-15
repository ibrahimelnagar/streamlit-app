"""
Cash Custody Management System
============================

A comprehensive personal finance tracking application with advanced transaction management features.

Created by: Ibrahim Elnagar
Role: Operation Manager
Created: December 2024

Features:
- Account Management (System and User accounts)
- Transaction Tracking (Deposits, Expenses, Transfers)
- Receipt Management
- Excel Export
- Data Reset Functionality
- Modern Bootstrap 5 UI

Copyright 2024 Ibrahim Elnagar. All rights reserved.
"""

import os
import sys
import logging
from datetime import datetime
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, send_file
from werkzeug.utils import secure_filename
import webbrowser
import threading
import sqlite3
import streamlit as st
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.debug = True  # Enable debug mode to see detailed error messages

# Constants
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
DB_FILENAME = 'cash_custody.db'

# Transaction Types
TRANSACTION_TYPES = {
    'TRANSFER': 'Transfer between accounts',
    'DEPOSIT': 'Deposit to account',
    'EXPENSE': 'Expense (pending reimbursement)',
    'REIMBURSE': 'Reimburse expense'
}

# System Accounts
SYSTEM_ACCOUNTS = {
    'MAIN': 'Main Account',
    'RECEIVABLE': 'Expenses Receivable'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_data_directory():
    """Get or create the data directory for the application."""
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    data_dir = os.path.join(application_path, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

def init_database():
    """Initialize SQLite database if it doesn't exist."""
    try:
        data_dir = get_data_directory()
        db_path = os.path.join(data_dir, DB_FILENAME)
        logger.info(f"Initializing database at: {db_path}")

        # Create new database connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create accounts table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                balance REAL DEFAULT 0,
                is_system BOOLEAN DEFAULT 0
            )
        ''')

        # Create transactions table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                from_account_id INTEGER,
                to_account_id INTEGER,
                receipt_path TEXT,
                reimbursed BOOLEAN DEFAULT 0,
                FOREIGN KEY (from_account_id) REFERENCES accounts (id),
                FOREIGN KEY (to_account_id) REFERENCES accounts (id)
            )
        ''')

        # Create system accounts if they don't exist
        logger.info("Checking system accounts...")
        for account_key, account_name in SYSTEM_ACCOUNTS.items():
            cursor.execute("SELECT id, name, balance, is_system FROM accounts WHERE name = ?", (account_name,))
            existing = cursor.fetchone()
            if existing:
                logger.info(f"Found existing system account: {existing}")
            else:
                logger.info(f"Creating system account: {account_name}")
                cursor.execute(
                    "INSERT INTO accounts (name, balance, is_system) VALUES (?, ?, 1)",
                    (account_name, 0)
                )

        # Verify all accounts in database
        cursor.execute("SELECT id, name, balance, is_system FROM accounts")
        all_accounts = cursor.fetchall()
        logger.info(f"All accounts in database: {all_accounts}")

        conn.commit()
        conn.close()

        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(os.path.dirname(db_path), '..', UPLOAD_FOLDER)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        st.error(f"Failed to initialize database: {str(e)}")
        return False

def get_db_connection():
    """Get a connection to the SQLite database."""
    try:
        data_dir = get_data_directory()
        db_path = os.path.join(data_dir, DB_FILENAME)
        logger.info(f"Opening database connection at: {db_path}")
        return sqlite3.connect(db_path)
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def get_accounts():
    """Get all accounts from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        logger.info("Executing SELECT query for accounts")

        # First check what's in the accounts table
        cursor.execute('SELECT * FROM accounts')
        all_accounts = cursor.fetchall()
        logger.info(f"All accounts in database (raw): {all_accounts}")

        # Now get the formatted accounts
        cursor.execute('SELECT id, name, balance, CAST(is_system AS INTEGER) FROM accounts ORDER BY name')
        accounts = cursor.fetchall()
        logger.info(f"Raw accounts data: {accounts}")
        result = [{'id': row[0], 'name': row[1], 'balance': row[2], 'is_system': bool(row[3])} for row in accounts]
        logger.info(f"Formatted accounts: {result}")
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error getting accounts: {str(e)}")
        return []

def get_transactions():
    """Get all transactions from the database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Join with accounts table to get account names
        cursor.execute('''
            SELECT t.id, t.date, t.type, t.description, t.amount,
                   t.from_account_id, t.to_account_id, t.receipt_path, t.reimbursed,
                   a1.name as from_account_name, a2.name as to_account_name
            FROM transactions t
            LEFT JOIN accounts a1 ON t.from_account_id = a1.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            ORDER BY t.date DESC, t.id DESC
        ''')

        transactions = cursor.fetchall()
        conn.close()

        # Convert to list of dictionaries
        return [{
            'id': t[0],
            'date': t[1],
            'type': t[2],
            'description': t[3],
            'amount': t[4],
            'from_account': t[9] if t[9] else 'External',  # Use account names instead of IDs
            'to_account': t[10] if t[10] else 'External',
            'receipt_path': t[7],
            'reimbursed': t[8]
        } for t in transactions]

    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return []

@app.route('/')
def index():
    accounts = get_accounts()
    transactions = get_transactions()
    transaction_types = {
        'DEPOSIT': 'Deposit',
        'EXPENSE': 'Expense',
        'TRANSFER': 'Transfer',
        'REIMBURSE': 'Reimburse'
    }
    return render_template('index_new_with_reset.html', accounts=accounts, transactions=transactions, transaction_types=transaction_types)

@app.route('/add_account', methods=['POST'])
def add_account():
    """Add a new account."""
    try:
        name = request.form['name']
        balance = float(request.form['balance'])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Log current accounts before adding
        cursor.execute('SELECT * FROM accounts')
        current_accounts = cursor.fetchall()
        logger.info(f"Current accounts before adding new one: {current_accounts}")

        cursor.execute(
            'INSERT INTO accounts (name, balance, is_system) VALUES (?, ?, ?)',
            (name, balance, 0)
        )

        # Log accounts after adding
        cursor.execute('SELECT * FROM accounts')
        updated_accounts = cursor.fetchall()
        logger.info(f"Updated accounts after adding new one: {updated_accounts}")

        # If initial balance is positive, create a transfer from main account
        if balance > 0:
            cursor.execute("""
                INSERT INTO transactions
                (date, type, description, amount, from_account_id, to_account_id)
                VALUES (?, 'TRANSFER', ?, ?,
                    (SELECT id FROM accounts WHERE name = ?),
                    (SELECT id FROM accounts WHERE name = ?))
            """, (datetime.now().strftime('%Y-%m-%d'), f'Initial balance for {name}',
                  balance, SYSTEM_ACCOUNTS['MAIN'], name))

            # Update main account balance
            cursor.execute("""
                UPDATE accounts
                SET balance = balance - ?
                WHERE name = ?
            """, (balance, SYSTEM_ACCOUNTS['MAIN']))

        conn.commit()
        conn.close()

        flash('Account added successfully!', 'success')
    except Exception as e:
        logger.error(f"Error adding account: {str(e)}")
        flash(f'Error adding account: {str(e)}', 'error')

    return redirect(url_for('index'))

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    """Add a new transaction."""
    try:
        logger.info("Received transaction request")
        logger.info(f"Form data: {request.form}")

        date = request.form['date']
        description = request.form['description']
        amount = float(request.form['amount'])
        transaction_type = request.form['type']

        logger.info(f"Processing {transaction_type} transaction for amount {amount}")

        # Handle file upload
        receipt_path = None
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                receipt_path = filename

        conn = get_db_connection()
        cursor = conn.cursor()

        if transaction_type == 'TRANSFER':
            from_account_id = int(request.form['from_account'])
            to_account_id = int(request.form['to_account'])

            logger.info(f"Transfer from account {from_account_id} to account {to_account_id}")

            # Add transaction
            cursor.execute("""
                INSERT INTO transactions
                (date, type, description, amount, from_account_id, to_account_id, receipt_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date, transaction_type, description, amount, from_account_id, to_account_id, receipt_path))

            # Update account balances
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

        elif transaction_type == 'DEPOSIT':
            to_account_id = int(request.form['to_account'])
            logger.info(f"Deposit to account {to_account_id}")

            # For deposits, we don't need a from_account - it's external money coming in
            cursor.execute("""
                INSERT INTO transactions
                (date, type, description, amount, to_account_id, receipt_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, transaction_type, description, amount, to_account_id, receipt_path))

            # Update account balance - just add to the target account
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_account_id))

            # Verify the balance was updated
            cursor.execute("SELECT balance FROM accounts WHERE id = ?", (to_account_id,))
            new_balance = cursor.fetchone()[0]
            logger.info(f"New balance for account {to_account_id}: {new_balance}")

        elif transaction_type == 'EXPENSE':
            from_account_id = int(request.form['from_account'])

            # Get receivable account ID
            cursor.execute("SELECT id FROM accounts WHERE name = ?", (SYSTEM_ACCOUNTS['RECEIVABLE'],))
            receivable_id = cursor.fetchone()[0]

            logger.info(f"Expense from account {from_account_id} to receivable account {receivable_id}")

            # Add transaction
            cursor.execute("""
                INSERT INTO transactions
                (date, type, description, amount, from_account_id, to_account_id, receipt_path, reimbursed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (date, transaction_type, description, amount, from_account_id, receivable_id, receipt_path))

            # Update account balances
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_account_id))
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, receivable_id))

        elif transaction_type == 'REIMBURSE':
            expense_id = int(request.form['expense_id'])

            # Get main and receivable account IDs
            cursor.execute("SELECT id FROM accounts WHERE name = ?", (SYSTEM_ACCOUNTS['MAIN'],))
            main_account_id = cursor.fetchone()[0]
            cursor.execute("SELECT id FROM accounts WHERE name = ?", (SYSTEM_ACCOUNTS['RECEIVABLE'],))
            receivable_id = cursor.fetchone()[0]

            logger.info(f"Reimbursing expense {expense_id}")

            # Mark original expense as reimbursed
            cursor.execute("UPDATE transactions SET reimbursed = 1 WHERE id = ?", (expense_id,))

            # Add reimbursement transaction
            cursor.execute("""
                INSERT INTO transactions
                (date, type, description, amount, from_account_id, to_account_id, receipt_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date, transaction_type, f"Reimbursement for expense #{expense_id}",
                  amount, receivable_id, main_account_id, receipt_path))

            # Update account balances
            cursor.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, receivable_id))
            cursor.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, main_account_id))

        conn.commit()
        logger.info("Transaction completed successfully")
        conn.close()

        flash('Transaction added successfully!', 'success')
    except Exception as e:
        logger.error(f"Error adding transaction: {str(e)}")
        flash(f'Error adding transaction: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/export_transactions')
def export_transactions():
    """Export transactions to Excel."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get transactions with account names
        cursor.execute('''
            SELECT
                t.date,
                t.type,
                t.description,
                t.amount,
                a1.name as from_account,
                a2.name as to_account,
                t.receipt_path,
                t.reimbursed
            FROM transactions t
            LEFT JOIN accounts a1 ON t.from_account_id = a1.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            ORDER BY t.date DESC, t.id DESC
        ''')

        transactions = cursor.fetchall()
        conn.close()

        # Create a pandas DataFrame
        df = pd.DataFrame(transactions, columns=[
            'Date', 'Type', 'Description', 'Amount',
            'From Account', 'To Account', 'Receipt Path', 'Reimbursed'
        ])

        # Format the DataFrame
        df['Amount'] = df['Amount'].apply(lambda x: f"{x:,.2f}")
        df['Reimbursed'] = df['Reimbursed'].apply(lambda x: 'Yes' if x else 'No')

        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Transactions', index=False)

            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Transactions']

            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4CAF50',
                'font_color': 'white',
                'border': 1
            })

            # Format header row
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Adjust column widths
            for i, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.set_column(i, i, max_length + 2)

        # Prepare the output
        output.seek(0)

        # Generate filename with current date
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error exporting transactions: {str(e)}")
        flash(f'Error exporting transactions: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/process_reimbursement', methods=['POST'])
def process_reimbursement():
    """Process reimbursement from Expenses Receivable to Main Account."""
    try:
        amount = float(request.form['amount'])
        description = request.form['description']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get system account IDs
        cursor.execute('SELECT id FROM accounts WHERE name = ?', ('Expenses Receivable',))
        expenses_receivable_id = cursor.fetchone()[0]

        cursor.execute('SELECT id FROM accounts WHERE name = ?', ('Main Account',))
        main_account_id = cursor.fetchone()[0]

        # Check if Expenses Receivable has sufficient balance
        cursor.execute('SELECT balance FROM accounts WHERE id = ?', (expenses_receivable_id,))
        expenses_balance = cursor.fetchone()[0]

        if expenses_balance < amount:
            flash('Insufficient balance in Expenses Receivable account!', 'error')
            conn.close()
            return redirect(url_for('index'))

        # Create the reimbursement transaction
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            INSERT INTO transactions
            (date, type, description, amount, from_account_id, to_account_id, reimbursed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (today, 'REIMBURSE', description, amount, expenses_receivable_id, main_account_id, 1))

        # Update account balances
        cursor.execute(
            'UPDATE accounts SET balance = balance - ? WHERE id = ?',
            (amount, expenses_receivable_id)
        )
        cursor.execute(
            'UPDATE accounts SET balance = balance + ? WHERE id = ?',
            (amount, main_account_id)
        )

        conn.commit()
        conn.close()

        flash('Reimbursement processed successfully!', 'success')
    except Exception as e:
        logger.error(f"Error processing reimbursement: {str(e)}")
        flash(f'Error processing reimbursement: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/reset_application', methods=['POST'])
def reset_application():
    try:
        logger.info("Resetting application data...")
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete all non-system accounts
        cursor.execute("DELETE FROM accounts WHERE is_system = 0")
        logger.info("Deleted all user accounts")

        # Reset system account balances to zero
        cursor.execute("UPDATE accounts SET balance = ? WHERE name = ?", (0.0, 'Main Account'))
        cursor.execute("UPDATE accounts SET balance = ? WHERE name = ?", (0.0, 'Expenses Receivable'))
        logger.info("Reset system account balances to zero")

        # Delete all transactions
        cursor.execute("DELETE FROM transactions")
        logger.info("Deleted all transactions")

        conn.commit()
        conn.close()

        flash('Application has been reset to initial state with zero balances', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error resetting application: {str(e)}")
        flash('Error resetting application data', 'danger')
        return redirect(url_for('index'))

def open_browser():
    """Open the browser to the application URL."""
    webbrowser.open('http://127.0.0.1:5000/')

if __name__ == '__main__':
    if init_database():
        # Start the Flask app in a separate thread
        from threading import Thread
        thread = Thread(target=lambda: app.run(debug=True, use_reloader=False))
        thread.start()

        # Use Streamlit to display the Flask app
        st.title("Cash Custody Management System")
        st.components.v1.html(f'<iframe src="http://127.0.0.1:5000/" width="100%" height="800"></iframe>', height=800)
    else:
        st.error("Failed to initialize the database.")
