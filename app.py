import streamlit as st
import json
from src.components.fetch_pdf_content import RBINotificationPDFExtractorTool
from src.components.fetch_rbi_links import RBIFetchTool
from src.components.elasticsearch_oper import ElasticSearchTool
from src.components.circular_analyzer import (run_analysis, create_analysis_task, create_circular_analyser,
                                              run_comparison, create_circular_comparator,create_comparison_task)
from src.utils.output_handler import capture_output

def main():
    st.set_page_config(page_title="RBI Compliance Tracker", layout="wide")
    st.title("RBI Compliance Tracker")

    # Ask the user for a date input
    user_date = st.date_input("Pick a date")
    # Convert the date to a string in the desired format
    date_str = user_date.strftime("%b %d, %Y")
    st.write(f"You selected: {user_date}")
    
    eb = ElasticSearchTool()
    if st.button(f"Check RBI circular"):
        st.info("Running CrewAI Agentic workflow...")
        with st.status("🤖 Extracting circular...", expanded=True) as status:
            try:
                final_analysis_result = []
                tool1 = RBIFetchTool()._run(date_str)
                tool2 = json.loads(RBINotificationPDFExtractorTool()._run(json.loads(tool1)))
                st.write(f"Total {len(tool2)} RBI circulars found for {date_str}")
                # Create persistent container for process output with fixed height.
                process_container = st.container(height=300, border=True)
                output_container = process_container.container()
                for circular_dict in tool2:
                    # Single output capture context.
                    with capture_output(output_container):
                        analyser = create_circular_analyser()
                        task = create_analysis_task(analyser, json.dumps(circular_dict))
                        result = run_analysis(analyser, task)
                        circular_dict.update(json.loads(result.raw))
                        eb.store_in_elastic(circular_dict)
                        final_analysis_result.append(circular_dict)
                status.update(label="Analysis completed and stored in ElasticSearch!", state="complete", expanded=False)
            except Exception as e:
                status.update(label="❌ Error occurred", state="error")
                st.error(f"An error occurred: {str(e)}")
                st.stop()

        # Create a list of options based on a unique field (like "id" or "name")
        options = [f"{record['name']}" for record in final_analysis_result]

        # Show the options in a selectbox
        selected_option = st.selectbox(f"Select a circular for {date_str}", options)
        # Extract the selected record based on the selected option
        selected_record = next(record for record in final_analysis_result if record["name"] == selected_option)

        st.header("Analysis of selected circular")
        # Display the full result for the selected record in the "Analysis" tab (left column)
        st.write(f"### Full details of {selected_record['name']}:")
        st.write(selected_record)
    
        st.header("Comparsion of selected circular with current company's policy")
        comparator = create_circular_comparator()
        comparison_task = create_comparison_task(comparator,selected_record)
        comp_result = run_comparison(comparator, comparison_task)
        st.write(json.loads(comp_result.raw))

if __name__ == "__main__":
    main()