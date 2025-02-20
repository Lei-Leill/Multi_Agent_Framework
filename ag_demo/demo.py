import requests
import autogen
import json
from fpdf import FPDF

# Define the Perplexity API endpoint
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_API_KEY = "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"

# Set a limit on API calls to control costs
MAX_API_CALLS = 20  
api_call_count = 0  

# Function to query Perplexity AI
def call_perplexity(messages, temperature=0.2, max_tokens=500):
    global api_call_count
    if api_call_count >= MAX_API_CALLS:
        return "API call limit reached. Please try again later."

    if not messages or not messages[-1]["content"].strip():
        return "Error: Empty message received."

    payload = {
        "model": "sonar",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9,
        "search_domain_filter": None,
        "return_images": False,
        "return_related_questions": False,
        "search_recency_filter": None,
        "top_k": 0,
        "stream": False,
        "presence_penalty": 0,
        "frequency_penalty": 1,
        "response_format": None
    }

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        api_call_count += 1
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        return f"Error: {response.status_code}, {response.text}"

# Research Collector Agent 🕵️‍♂️
class ResearchCollector(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Collects and returns reliable sources from Perplexity AI."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Collected sources:\n{response_text}"}

# Summarization Agent 📝
class SummarizationAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Summarizes the information collected by the research agent."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Summary:\n{response_text}"}

# Verification Agent ✅
class VerificationAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Checks the reliability of the summary."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Verified Information:\n{response_text}"}

# Report Generator Agent 📄
class ReportGenerator(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Formats the collected, summarized, and verified data into JSON and a PDF report."""

        # Extract content from all previous messages
        collected_sources = ""
        summary = ""
        verification = ""

        for msg in messages:
            content = msg.get("content", "")
            if "Collected sources" in content:
                collected_sources = content.replace("Collected sources:\n", "")
            elif "Summary" in content:
                summary = content.replace("Summary:\n", "")
            elif "Verified Information" in content:
                verification = content.replace("Verified Information:\n", "")

        # Create structured JSON report
        report_data = {
            "Impact Analysis Report": {
                "Sources": collected_sources.strip(),
                "Summary": summary.strip(),
                "Verification": verification.strip()
            }
        }

        json_filename = "impact_analysis.json"
        with open(json_filename, "w") as json_file:
            json.dump(report_data, json_file, indent=4)

        # Generate PDF report
        pdf_filename = "impact_analysis.pdf"
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", style="B", size=16)
        pdf.cell(190, 10, "Impact Analysis Report", ln=True, align='C')

        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(190, 10, "Sources", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(190, 8, collected_sources.strip())

        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(190, 10, "Summary", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(190, 8, summary.strip())

        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(190, 10, "Verification", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(190, 8, verification.strip())

        pdf.output(pdf_filename)

        return {"role": "assistant", "content": f"Report generated successfully: {json_filename} and {pdf_filename}"}
    
# Instantiate the Agents
research_agent = ResearchCollector(name="ResearchCollector")
summary_agent = SummarizationAgent(name="SummarizationAgent")
verification_agent = VerificationAgent(name="VerificationAgent")
report_agent = ReportGenerator(name="ReportGenerator")

# Create the user proxy agent
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=5,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    system_message="You are conducting impact analysis research."
)

# Define the impact analysis task
task = """
Perform an impact analysis on AI in education. 
Collect reliable sources, summarize key findings, verify the accuracy, 
and generate a structured report in JSON and PDF format.
"""

# Start the interaction: Research Phase
user_proxy.initiate_chat(research_agent, message=task)

# Summarization Phase
summary_task = "Summarize the findings from the research collection."
user_proxy.initiate_chat(summary_agent, message=summary_task)

# Verification Phase
verification_task = "Verify the accuracy and reliability of the summarized research."
user_proxy.initiate_chat(verification_agent, message=verification_task)

# Report Generation Phase
report_task = "Format the verified information into a structured report with JSON and a PDF file."
user_proxy.initiate_chat(report_agent, message=report_task)