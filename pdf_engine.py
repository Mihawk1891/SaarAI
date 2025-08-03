from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
import qrcode
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
import logging
from ssl import create_default_context
import ssl

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

class PDFEngine:
    def __init__(self):
        self.styles = self._create_styles()
    
    def _create_styles(self):
        styles = getSampleStyleSheet()
        
        # Base style
        styles.add(ParagraphStyle(
            name='BaseStyle',
            fontName='Helvetica',
            fontSize=10,
            leading=15,
            spaceAfter=10,
            alignment=TA_LEFT
        ))
        
        # ADHD style
        styles.add(ParagraphStyle(
            name='ADHD',
            parent=styles['BaseStyle'],
            fontSize=10,
            leading=15,
            spaceAfter=8,
            borderPadding=5,
            backColor=colors.HexColor('#E6F2FF')  # Light blue
        ))
        
        # Low vision style
        styles.add(ParagraphStyle(
            name='LowVision',
            parent=styles['BaseStyle'],
            fontSize=14,
            leading=20,
            textColor=colors.black,
            backColor=colors.white
        ))
        
        return styles
    
    def create_pdf(self, content, acc_pref, output_path):
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            story = []
            
            # Apply accessibility settings
            style_name = self._get_style_for_preference(acc_pref)
            
            # Split into paragraphs
            paragraphs = content.split('\n\n')
            
            for para in paragraphs:
                if para.strip():
                    p = Paragraph(para.strip(), self.styles[style_name])
                    story.append(p)
                    story.append(Spacer(1, 12))
            
            # Add feedback QR
            qr_img = self._generate_qr_code(output_path)
            story.append(Image(qr_img, width=100, height=100))
            
            doc.build(story)
            logger.info(f"PDF created at {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"PDF creation failed: {e}")
            raise
    
    def _generate_qr_code(self, report_path):
        # Ensure directory exists
        os.makedirs('temp', exist_ok=True)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        report_id = os.path.basename(report_path).split('_')[0]
        qr.add_data(f"https://feedback.scoreazy.com?report={report_id}")
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_path = f"temp/{report_id}_feedback.png"
        qr_img.save(qr_path)
        return qr_path
    
    def _get_style_for_preference(self, pref):
        mapping = {
            'dyslexic': 'BaseStyle',  # Fallback to base style
            'adhd': 'ADHD',
            'low-vision': 'LowVision'
        }
        return mapping.get(pref.lower(), 'BaseStyle')
    
    def deliver_report(self, pdf_path, email, lang):
        if not email or '@' not in email:
            logger.warning(f"Skipping delivery for invalid email: {email}")
            return
            
        try:
            # Email configuration
            msg = MIMEMultipart()
            msg['Subject'] = self._get_subject(lang)
            msg['From'] = os.getenv('SMTP_USER')
            msg['To'] = email
            
            # Add body
            body = self._get_email_body(lang)
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            with open(pdf_path, "rb") as f:
                attach = MIMEApplication(f.read(), _subtype="pdf")
                attach.add_header('Content-Disposition', 'attachment', 
                                filename=os.path.basename(pdf_path))
                msg.attach(attach)
            
            # Send email
            use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
            if use_ssl:
                server = smtplib.SMTP_SSL(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
            else:
                server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
                server.starttls(context=ssl.create_default_context())
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
            server.send_message(msg)
            logger.info(f"Report delivered to {email}")
        except Exception as e:
            logger.error(f"Email delivery failed for {email}: {e}")
    
    def _get_subject(self, lang):
        subjects = {
            'en': "Your Scoreazy Learning Report",
            'hi': "आपकी स्कोरज़ी रिपोर्ट",
            'es': "Su informe de aprendizaje Scoreazy",
            'fr': "Votre rapport d'apprentissage Scoreazy",
            'ar': "تقرير سكوريزي التعليمي الخاص بك"
        }
        return subjects.get(lang, subjects['en'])
    
    def _get_email_body(self, lang):
        bodies = {
            'en': "Find attached your personalized learning report from Scoreazy\n\n",
            'hi': "स्कोरज़ी से आपकी व्यक्तिगत लर्निंग रिपोर्ट संलग्न है\n\n",
            'es': "Adjunto encontrará su informe de aprendizaje personalizado de Scoreazy\n\n",
            'fr': "Ci-joint votre rapport d'apprentissage personnalisé de Scoreazy\n\n",
            'ar': "تجد في المرفق تقرير التعلم الشخصي الخاص بك من سكوريزي\n\n"
        }
        base = bodies.get(lang, bodies['en'])
        return base + "Please scan the QR code to provide feedback on this report."