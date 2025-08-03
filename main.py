import pandas as pd
from data_processor import DataProcessor
from report_generator import ReportGenerator
from pdf_engine import PDFEngine
from privacy_manager import PrivacyManager
import datetime
import os
import logging
from dotenv import load_dotenv



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def generate_reports():
    # Create required directories
    for dir_path in ['reports', 'temp', 'teacher_audio']:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")
    
    # Load and process data
    processor = DataProcessor()
    try:
        df = processor.load_data()
        validated_df = processor.validate_data(df)
        logger.info(f"Loaded {len(validated_df)} student records")
    except Exception as e:
        logger.error(f"Data loading failed: {e}")
        return
    
    # Generate reports
    report_gen = ReportGenerator()
    pdf_engine = PDFEngine()
    
    for _, row in validated_df.iterrows():
        student_id = row['StudentID']
        logger.info(f"Processing student: {student_id}")
        
        try:
            # Generate insights
            analysis = report_gen.analyze_scores(row)
            vark_profile = report_gen.classify_vark(row)
            
            # Get teacher quote
            teacher_quote = processor.get_teacher_quote(student_id)
            
            # Generate report content
            report_content = report_gen.generate_narrative(
                row, 
                analysis, 
                vark_profile,
                teacher_quote=teacher_quote
            )
            
            # Create PDF
            pdf_path = f"reports/{student_id}_report.pdf"
            pdf_engine.create_pdf(report_content, row['AccPref'], pdf_path)
            
            # Deliver report
            if row.get('ContactEmail'):
                pdf_engine.deliver_report(
                    pdf_path, 
                    row['ContactEmail'], 
                    row['LangPref']
                )
                logger.info(f"Report delivered for {student_id}")
        except Exception as e:
            logger.error(f"Error processing student {student_id}: {e}")
    
    # Initiate privacy cleanup
    PrivacyManager().schedule_deletion(datetime.datetime.now() + datetime.timedelta(hours=24))
    logger.info("Scheduled data cleanup")

if __name__ == "__main__":
    try:
        generate_reports()
    except Exception as e:

        logger.error(f"Fatal error in generate_reports: {e}")
