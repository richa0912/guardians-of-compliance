import logging
import requests
import fitz
from pydantic import BaseModel, HttpUrl, Field, ConfigDict
import json
from typing import List, Type, Dict, Any
from crewai.tools import BaseTool
from elasticsearch import Elasticsearch

# ✅ Enable Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Pydantic model for a notification
class RBINotificationPDFExtractorInput(BaseModel):
    """Input Schema for RBINotificationPDFExtractorTool"""
    name: str = Field(..., description="Name of the RBI circulars")
    notification_url: HttpUrl = Field(..., description="NOTIF of the RBI circulars")
    pdf_url: HttpUrl = Field(..., description="PDF URL of the RBI circulars")
    circular_date: str = Field(..., description="Date of the RBI circulars")


class RBINotificationPDFExtractorTool:
    name: str = "RBI fetch pdf content"
    description: str = "Fetches the pdf content from the pdf url"
    args_schema: Type[BaseModel] = RBINotificationPDFExtractorInput

    def download_pdf(self, pdf_url, save_path):
        try:
            # Send a GET request to the PDF URL
            response = requests.get(pdf_url, stream=True)

            # Check if the request was successful
            if response.status_code == 200:
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                logging.debug(f"Downloaded PDF successfully: {save_path}")
                return save_path
            else:
                logging.error(f"Failed to download PDF: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error downloading PDF: {str(e)}")
            return None


    def read_pdf(self, pdf_path):
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                full_text += page.get_text("text")
            return full_text
        except Exception as e:
            logging.error(f"Error reading PDF: {str(e)}")
            return None

    def process_notification(self, notification):
        name = notification.get("name")
        pdf_url = notification.get("pdf_url")
        notification_url = notification.get("notification_url")
        circular_date = notification.get("circular_date")
        output = {}

        # Download and read from the direct PDF URL
        logging.debug(f"Processing PDF for: {name}")
        pdf_file_path = pdf_url.split('/')[-1]  # Limit the name for the file path
        downloaded_url = self.download_pdf(pdf_url, pdf_file_path)
        if downloaded_url:
            pdf_text = self.read_pdf(downloaded_url)
            output = {
                "name": name,
                "pdf_url": pdf_url,
                "notification_url": notification_url,
                "circular_text": pdf_text,
                "downloaded_url": downloaded_url,
                "circular_date": circular_date
            }
        return output
    
    def _run(self, notifications: List[RBINotificationPDFExtractorInput]) -> list:
        print(f"inside run with arguments==={notifications}")
        # Process each notification and print JSON output
        output_list = []
        for notification in notifications:
            result = self.process_notification(notification)
            if result:
                output_list.append(result)
        # Convert the result to JSON format
        output_json = json.dumps(output_list, indent=4)
        logging.info(f"Getting pdf content from the URL: {output_json}")
        return output_json
        # return output_list
    