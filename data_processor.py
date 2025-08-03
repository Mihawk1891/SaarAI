import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
from dotenv import load_dotenv
import logging

# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

class DataProcessor:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = self._get_credentials()
    
    def _get_credentials(self):
        """Handle credentials from file or JSON (Windows-safe)"""
        service_account_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        service_account_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

        # If full JSON is provided in .env
        if service_account_json:
            try:
                creds_data = json.loads(service_account_json)
                logger.info("Using credentials from JSON string in environment.")
                return Credentials.from_service_account_info(creds_data, scopes=self.scopes)
            except Exception as e:
                logger.error(f"Failed to load credentials from JSON: {e}")

        # If a file path is provided
        if service_account_file:
            service_account_file = service_account_file.strip('"')  # Remove quotes
            logger.info(f"Using credentials file: {service_account_file}")
            if os.path.exists(service_account_file):
                return Credentials.from_service_account_file(service_account_file, scopes=self.scopes)
            else:
                logger.error(f"Credentials file not found at: {service_account_file}")

        # Try application default credentials
        try:
            from google.auth import default
            creds, _ = default(scopes=self.scopes)
            logger.info("Using application default credentials")
            return creds
        except Exception as e:
            logger.error(f"Failed to get application default credentials: {e}")

        # Fallback to sample data
        logger.warning("Using sample data mode without Google credentials")
        return None
    
    def load_data(self):
        """Load data from Google Sheets or use sample data"""
        try:
            if self.creds:
                gc = gspread.authorize(self.creds)
                sheet_id = os.getenv('GOOGLE_SHEETS_ID')
                if not sheet_id:
                    raise ValueError("Google Sheets ID not configured")
                
                sheet = gc.open_by_key(sheet_id).sheet1
                data = sheet.get_all_records()
                logger.info(f"Loaded {len(data)} records from Google Sheets")
                return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Error loading data from Google Sheets: {e}")
        
        # Fallback to sample data
        logger.info("Using sample data for testing")
        return pd.DataFrame({
            'StudentID': [101, 102],
            'StudentName': ['John Doe', 'Jane Smith'],
            'Math_C': [85, 75],
            'Math_P1': [72, 68],
            'Math_P2': [68, 65],
            'Science_C': [92, 85],
            'Science_P1': [88, 82],
            'VARK_Q1': ['A', 'B'],
            'VARK_Q2': ['A', 'B'],
            'VARK_Q3': ['B', 'A'],
            'VARK_Q4': ['A', 'B'],
            'LangPref': ['en', 'hi'],
            'AccPref': ['standard', 'dyslexic'],
            'ContactEmail': ['test1@example.com', 'test2@example.com']
        })
    
    def validate_data(self, df):
        """Validate and clean input data"""
        critical_cols = ['StudentID', 'Math_C', 'Science_C', 'LangPref']
        
        # Check for missing critical columns
        missing_cols = [col for col in critical_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing critical columns: {', '.join(missing_cols)}")
            for col in missing_cols:
                df[col] = None
        
        # Drop rows missing critical values
        df = df.dropna(subset=critical_cols, how='any')
        
        # Fill defaults
        df['AccPref'] = df['AccPref'].fillna('standard')
        df['ContactEmail'] = df['ContactEmail'].fillna('')
        df['LangPref'] = df['LangPref'].fillna('en')
        
        # Fill VARK questions safely
        for i in range(1, 5):
            col = f'VARK_Q{i}'
            if col in df.columns:
                df[col] = df[col].fillna('A')
            else:
                df[col] = 'A'
        
        return df
    
    def get_teacher_quote(self, student_id):
        """Get teacher quote (stub)"""
        quotes = [
            "Shows excellent problem-solving skills",
            "Very engaged during class discussions",
            "Needs to work on completing assignments on time",
            "Demonstrates strong analytical thinking"
        ]
        return quotes[hash(student_id) % len(quotes)]
