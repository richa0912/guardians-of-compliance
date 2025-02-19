from typing import Type
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tasks import TaskOutput
from dotenv import load_dotenv
import os
from elasticsearch import Elasticsearch

load_dotenv()

### AGENT 1
def create_circular_analyser():
    analyser = Agent(
        role='Compliance Officer',
        goal='Analyse RBI circulars and identify all compliance requirements mentioned within the document thoroughly',
        backstory='Expert at analyzing RBI circulars and summarizing complex information and compliance requirements for the company',
        verbose=True,
        allow_delegation=True,  # Disable delegation to avoid caching
    )
    return analyser

### AGENT 2
def create_circular_comparator():
    comparator = Agent(
        role='Compliance Policies Comparator',
        goal='Compare RBI circular and elasticsearch stored company policy and highlight key differences and recommend next steps',
        backstory='Expert at analyzing RBI circulars and compare with company existing policy for compliance requirements',
        verbose=True,
        # allow_delegation=True,  # Disable delegation to avoid caching
    )
    return comparator

##### TASK 1
def create_analysis_task(analyser, context):
    """Create a research task for the agent to execute.
    
    Args:
        analyser (Agent): The research agent that will perform the task
        task_description (str): The research query or topic to investigate
    
    Returns:
        Task: A configured CrewAI task with expected output format
    """
    return Task(
        description=f"""Given the text of an RBI circular, identify the different compliance types mentioned within the circular.
    There may be multiple compliance types in a single circular. For each identified compliance type, provide the specific type
    of compliance it refers to. The compliance types can be classified from Know Your Customer, Anti-Money Laundering,
    Grievance Redressal Mechanism, Loan Restructuring, Export-Import Control, and Foreign Exchange Management Act.
    Do not retrieve any other compliance type than the ones mentioned, if these are not present leave the field empty.
    For each compliance type identified, mention the relevant section(s) of the circular that refers to it. If the circular refers to multiple compliance types, list all applicable types
    and their corresponding sections with detailed description. Additionally, summarize the key updates and changes introduced
    in the circular ensuring that you highlight the regulatory requirements, new processes, and any deadlines that are relevant for compliance.
    context: {context}""",
        expected_output="""A comprehensive analysis report for the circular.
        The report must be detailed, focusing on the most significant and impactful findings.
        Strictly format the output in JSON format as follows
        {
        "summary": "Provide a brief summary of the circular’s updates and changes here",
        "compliance_types": "Provide full list of identified tags like KYC Compliance, GRM Compliance, AML Complaince"
        "compliance_types_details": 'Provide detailed description of identified tags here in below format
        [
        {
        "type": "KYC Compliance",
        "sections": ["2.1", "3.4"],
        "description": "Updated KYC requirements for banks ..."
        },
        {
        "type": "GRM Compliance",
        "sections": ["5.2"],
        "description": "Guidelines for setting up a grievance redressal mechanism ..."
        }]}
        }'
        Do not give extra reasoning which is not in JSON format.
        """,
        agent=analyser
    )

#### TASK 2
def create_comparison_task(comparator,context):
    return Task(
        description=f"""Compare the RBI circular with the stored company policy for the compliance tags identified and
        highlight all possible regulatory key differences. You retrieve latest RBI circulars from ElasticSearch Index "rbi_kyc_circulars",
        compare them together and highlight what's been missing into the company's policy with prioritised actionable insights.
        Recommend next steps for company policy adjustments to updates its policy if required to be compliant and possible risk mitigations
        RBI circular: {context}""",
        expected_output="""A comprehensive comparison report for the RBI circular with company exisitng policy.
        Format of the report should be as following:
        {
        "Compliant Flag": "'Needs immediate action or not' after comparing both circulars
        "comparison updates": [
            {
                "category": "Policy Alignment",
                "rbi_reference": "RBI Circular XYZ-2024",
                "company_reference": "Company Policy ABC-2023",
                "key_differences": "The company policy lacks updates regarding FATF recommendations."
            },
            {
                "category": "Regulatory Changes",
                "rbi_reference": "RBI Circular XYZ-2024",
                "company_reference": "Company Policy ABC-2023",
                "key_differences": "New due diligence requirements are missing from the company policy."
            }
        ],
        "action_items": [
            {
                "priority": "High",
                "recommendation": "Company policy should be updated to reflect the new FATF compliance requirements."
            },
            {
                "priority": "Medium",
                "recommendation": "Company should revise customer verification timelines in accordance with RBI updates."
            }
            ],
        "risk mitigations": ...
        }
        """,
        agent=comparator,
    )

#--------------------------------#
#         Analyser Crew          #
#--------------------------------#
def run_analysis(analyser, task):
    """Execute the research task using the configured agent.
    
    Args:
        analyser (Agent): The research agent to perform the task
        task (Task): The research task to execute
    
    Returns:
        str: The research results in markdown format
    """
    crew = Crew(
        agents=[analyser],
        tasks=[task],
        verbose=True,
        process=Process.sequential
    )

    return crew.kickoff()

#--------------------------------#
#         Comparator Crew          #
#--------------------------------#
def run_comparison(comparator, task):
    """Execute the research task using the configured agent.
    
    Args:
        analyser (Agent): The research agent to perform the task
        task (Task): The research task to execute
    
    Returns:
        str: The research results in markdown format
    """
    crew = Crew(
        agents=[comparator],
        tasks=[task],
        verbose=True,
        process=Process.sequential
    )

    return crew.kickoff()