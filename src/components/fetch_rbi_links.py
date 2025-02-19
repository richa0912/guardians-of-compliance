import logging
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from crewai.tools import BaseTool
from typing import Type, Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, model_validator, ValidationError

# Base URL of the RBI Notification Page
BASE_URL = "https://www.rbi.org.in/Scripts/NotificationUser.aspx"
# ✅ Enable Logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Define the Pydantic model for input validation
class RBIFetchToolInput(BaseModel):
    """Input schema for RBIFetchTool"""
    date: str
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None

    # Validator to ensure the date is valid
    @model_validator(mode="before")
    def validate_date(cls, values):
        date_str = values.get('date')
        try:
            # Attempt to parse the date using the format "Feb 13, 2025"
            date_obj = datetime.strptime(date_str, '%b %d, %Y')
        except ValueError:
            raise ValueError('Date must be in the format "Feb 13, 2025".')

        # Extract day, month, and year
        values['day'] = date_obj.day
        values['month'] = date_obj.month
        values['year'] = date_obj.year
        return values

class RBIFetchToolOutput(BaseModel):
    """Schema for a single notification"""
    name: str
    notification_url: str
    pdf_url: str
    circular_date: str

class RBIFetchTool(BaseTool):
    "Tool to fetch RBI circulars"
    name: str = "RBI Fetch Circular Links"
    description: str = "Fetches the latest RBI circulars from the RBI website given the date as input"
    args_schema: Type[BaseModel] = RBIFetchToolInput

    # Function to fetch the form data (e.g., __VIEWSTATE, __EVENTVALIDATION)
    def fetch_form_data(self, session):
        """ Fetch the form data (e.g., __VIEWSTATE, __EVENTVALIDATION) """
        response = session.get(BASE_URL)
        
        if response.status_code != 200:
            logging.error("Failed to fetch the page.")
            return None

        # Parse the page content using BeautifulSoup
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Extract hidden fields from the form
        viewstate = soup.find("input", {"name": "__VIEWSTATE"})["value"]
        eventvalidation = soup.find("input", {"name": "__EVENTVALIDATION"})["value"]
        viewstategenerator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"})["value"]
        
        # You can also extract the __EVENTTARGET and __EVENTARGUMENT values if required
        return {
            "__VIEWSTATE": viewstate,
            "__EVENTVALIDATION": eventvalidation,
            "__VIEWSTATEGENERATOR": viewstategenerator
        }

    def fetch_notifications_for_date(self, input_date, session):
        """ Fetch notifications for the input date """
        # Fetch the form data first
        form_data = self.fetch_form_data(session)
        if not form_data:
            return {}
        # Add the year and month to the form data
        inp_date, year, month = input_date.date, input_date.year, input_date.month
        form_data["hdnYear"] = str(year)
        form_data["hdnMonth"] = str(month)  # You can set this to 0 if you want to fetch all months

        # Send a POST request to submit the form
        response = session.post(BASE_URL, data=form_data)

        if response.status_code != 200:
            logging.error(f"Failed to fetch data for {year}-{month}.")
            return {}

        # Parse the response content
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find the content div that contains the notifications
        content_div = soup.find('div', {'id': 'pnlDetails'})
        
        if not content_div:
            logging.error("Failed to find the content area.")
            return {}

        # Extract all notifications and PDF links
        notifications = {}
        table_rows = content_div.find_all('tr')
        
        current_date = None
        current_notifications = []

        for row in table_rows:
            # Look for date headers
            date_header = row.find('td', class_='tableheader')

            if date_header:
                if current_date:
                    notifications[current_date] = current_notifications
                current_date = date_header.get_text(strip=True)
                current_notifications = []

            elif current_date==inp_date:
                # Extract notification and PDF link data
                notification_link = row.find('a', class_='link2')
                pdf_link_tag = row.find_all('a', href=True)

                if notification_link:
                    notification_name = notification_link.get_text(strip=True)
                    notification_url = notification_link.get('href')

                    # Extract the PDF link
                    pdf_url = None
                    if len(pdf_link_tag) > 1:
                        pdf_url = pdf_link_tag[1]['href']
                        pdf_url = urljoin(BASE_URL, pdf_url)

                    # Append notification data
                    current_notifications.append({
                        'name': notification_name,
                        'notification_url': urljoin(BASE_URL, notification_url),
                        'pdf_url': pdf_url,
                        'circular_date': inp_date
                    })

        # Append the last set of notifications
        if current_date:
            notifications[current_date] = current_notifications

        return notifications[inp_date]

    def _run(self, date: str) -> list:
        """ function to run the tool """
        try:
            print(f"inside rbi link fetch run function {date}")
            validated_input = self.args_schema(date=date)

            # Create a session to persist cookies
            session = requests.Session()
            print(f"Fetching circular links from RBI website for date {validated_input}")

            # Fetch notifications for the specific year and month
            notifications = self.fetch_notifications_for_date(validated_input, session)

            if notifications:
                # print(json.dumps(notifications, indent=4))
                return json.dumps(notifications, indent=4)

            logging.debug(f"No notifications found for {validated_input}.")
            return []

        except ValueError as e:
            logging.error(f"Invalid input: {e}")
            return []
        except ValidationError as e:
            logging.error(f"Validation error: {e}")
            return []
