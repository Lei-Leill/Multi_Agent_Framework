import requests
from bs4 import BeautifulSoup
import autogen
import json
from fpdf import FPDF

# Define the Perplexity API endpoint
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_API_KEY = "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"

# Set a limit on API calls to control costs
MAX_API_CALLS = 20  
api_call_count = 0  

shared_memory = {} 

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


# Function to parse the website content
def parse_website(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        return f"Error: {str(e)}"

# Website Parsing Agent
class WebsiteParsingAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Parses the website and extracts relevant data for counterfactual analysis."""
        url = messages[-1].get("content", "").strip()  # Assume the user provides the URL as the last message
        if url:
            parsed_data = parse_website(url)
            summarized_text = call_perplexity([
                {"role": "system", "content": "Summarize the following website content in a concise and informative way."},
                {"role": "user", "content": parsed_data}
            ])
            # Pass the parsed data into the counterfactual analysis
            shared_memory["website_text"] = summarized_text 
            return {"role": "assistant", 
                    "content": f"Parsed data from the website:\n{summarized_text}",
                    "data": {"website_text": summarized_text}}
        else:
            return {"role": "assistant", "content": "Error: No URL provided."}


class ScenarioIdentificationAgent(autogen.AssistantAgent):
    def __init__(self, name, data, **kwargs):
        super().__init__(name=name, **kwargs)  # Properly pass 'name' to superclass AssistantAgent
        self.website_data = data  # Store extracted website data
    
    def generate_reply(self, messages, sender, **kwargs):
        """Generates counterfactual scenarios based on extracted website data using Perplexity API."""

        counterfac_exp = "Generate a structured list of counterfactual scenarios that describe \
            alternative outcomes in the absence of the product/ service of the comapny. \
            Ensure that these counterfactuals are realisticand provide measurable differences in impact.\
            For each counterfactual scenario:\
            Identify the most likely alternative actions or conditions that would exist without the intervention.\
            Ensure each counterfactual is quantifiable, providing measurable impact differences where possible.\
            If exact data is unavailable, suggest proxy metrics or calculations that can approximate the missing values.\
            Ensure all assumptions are logically sound and avoid speculative or unsupported claims.\
            Format the response as a structured output, where each counterfactual scenario includes:\
            Scenario Name: A clear title for the counterfactual, and should be a common key word used in research and report\
            Unit: A likely unit commonly used in research and can lead us to quatified impact\
            Description: A short explanation of what happens in the absence of the intervention.\
            Expected Impact: A  difference compared to the original intervention.\
            Relevant Data Points: Any supporting research, statistics, or calculations to validate the scenario.\
            At the end, list the sources used with citation"
        # Call Perplexity API to generate counterfactuals
        response_text = call_perplexity([
            {"role": "system", "content": f"Generate two counterfactuals based on the given company website text. The standard is {counterfac_exp}"},
            {"role": "user", "content": self.website_data}
        ])

        return {
            "role": "assistant",
            "content": f"Top counterfactuals:\n{response_text}"
        }

# Data Retrieval Agent
class DataRetrievalAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Retrieves relevant data for the identified counterfactuals."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Retrieved data:\n{response_text}"}

# Citation Validation Agent
class CitationValidationAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Verifies the validity of the data sources."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Verified citations:\n{response_text}"}

# Data Accuracy Agent
class DataAccuracyAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Ensures the accuracy of counterfactual data and adjusts where necessary."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Revised counterfactuals:\n{response_text}"}


def main():
    # Create the user proxy agent to allow human interaction with o
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="ALWAYS",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        system_message="You are an expert in Impact Analysis. Your ultimate task is to compile a list that \
            includes metrics, counterfactuals, first-order outcomes, second-order outcomes, and costs that \
            this company can directly measure. It is crucial that metrics, counterfactuals, first-order outcomes,\
            second-order outcomes, and costs are quantifiable. \Each output must:\
            1. **Include Quantifiable Metrics** - Ensure that all values provided are measurable and align with real-world impact frameworks.\
            2. **Assess Counterfactuals** - Identify and validate alternative scenarios to provide comparative insights.\
            3. **Evaluate Outcomes** - Distinguish between first-order (direct) and second-order (indirect) outcomes.\
            4. **Validate Research & Sources** - Pull relevant research, verify citations, and cross-check for hallucinations or inconsistencies.\
            5. **Align with Impact Standards** - Ensure outputs align with relevant sustainability and impact measurement frameworks such as SDGs, IRIS+, and others.",
        code_execution_config={"use_docker": False}
    )

    # Instantiate the Agents
    website_parsing_agent = WebsiteParsingAgent(name="WebsiteParsingAgent")

    website_task = "Provide a website URL for counterfactual analysis."
    user_proxy.initiate_chat(website_parsing_agent, message=website_task)

    scenario_agent = ScenarioIdentificationAgent(name="ScenarioIdentificationAgent", data = shared_memory["website_text"])

    # Step 3: Pass extracted website data to Scenario Identification Agent
    user_proxy.initiate_chat(scenario_agent, message="Generate counterfactual scenarios based on extracted website data.")


if __name__ == "__main__":
    main()


'''
# Website Parsing Agent
class WebsiteParsingAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Parses the website and extracts relevant data for counterfactual analysis."""
        url = messages[-1].get("content", "").strip()  # Assume the user provides the URL as the last message
        if url:
            parsed_data = parse_website(url)
            # Pass the parsed data into the counterfactual analysis
            return {"role": "assistant", "content": f"Parsed data from the website:\n{parsed_data}"}
        else:
            return {"role": "assistant", "content": "Error: No URL provided."}

# Scenario Identification Agent
class ScenarioIdentificationAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Generates counterfactual scenarios based on extracted website data."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Top 2 counterfactuals for '[Metric Name]':\n{response_text}"}

# Data Retrieval Agent
class DataRetrievalAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Retrieves relevant data for the identified counterfactuals."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Retrieved data:\n{response_text}"}

# Citation Validation Agent
class CitationValidationAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Verifies the validity of the data sources."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Verified citations:\n{response_text}"}

# Data Accuracy Agent
class DataAccuracyAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Ensures the accuracy of counterfactual data and adjusts where necessary."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Revised counterfactuals:\n{response_text}"}

# Instantiate the Agents
website_parsing_agent = WebsiteParsingAgent(name="WebsiteParsingAgent")
scenario_agent = ScenarioIdentificationAgent(name="ScenarioIdentificationAgent")
data_retrieval_agent = DataRetrievalAgent(name="DataRetrievalAgent")
citation_validation_agent = CitationValidationAgent(name="CitationValidationAgent")
data_accuracy_agent = DataAccuracyAgent(name="DataAccuracyAgent")

# Create the user proxy agent
user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=5,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    system_message="You are conducting counterfactual impact analysis research."
)

# Define the task for counterfactual analysis
counterfactual_task = """
Please provide a website URL. I will parse the content of the website and perform a counterfactual analysis on the extracted data. 
This includes generating alternative scenarios, collecting data, verifying citations, and ensuring data accuracy.
"""

# Start the interaction: Website Parsing Phase (first step)
user_proxy.initiate_chat(website_parsing_agent, message=counterfactual_task)

scenario_task = "Identify 2 alternative scenarios without the product or service of the company based on information from the website"
user_proxy.initiate_chat(scenario_agent, message=scenario_task)

# After parsing, proceed with counterfactual analysis steps
data_task = "Collect relevant data for each alternative scenario."
user_proxy.initiate_chat(data_retrieval_agent, message=data_task)

# Citation Validation Phase
validation_task = "Verify the citations for the collected data."
user_proxy.initiate_chat(citation_validation_agent, message=validation_task)

# Data Accuracy Phase
accuracy_task = "Ensure the accuracy of the data and calculate approximations if necessary."
user_proxy.initiate_chat(data_accuracy_agent, message=accuracy_task)

'''