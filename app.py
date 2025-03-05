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
def call_perplexity(messages, temperature=0.2, max_tokens=1000):
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
        "top_k": 5,
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

        counterfac_exp = "Conduct an **internet-wide search**, including academic papers, government reports, and industry sources, to generate a \
            structured list of counterfactual scenarios analyzing alternative outcomes in the absence of company's product or service. \
                \
                ### **Counterfactual Scenario Requirements**: \
                - **Realistic & Research-Based**: Ensure counterfactuals are **real-world plausible** and grounded in **verified data**. \
                - **Measurable Impact**: Provide **quantifiable comparisons**, using research-based metrics where available. \
                - **Alternative Conditions**: Identify the most **likely alternative** actions, processes, or materials that would be used instead. \
                - **Proxy Metrics for Missing Data**: If exact data is unavailable, suggest **proxy indicators** or approximate calculations. \
                - **Avoid Unsupported Claims**: Ensure **logical soundness**, avoiding speculation without factual support. \
                \
                ### **Structured Output Format**: \
                For each counterfactual scenario, structure the response as follows: \
                1. **Scenario Name**: A clear title, using terminology commonly found in **academic research, reports, or industry studies**. \
                2. **Unit of Measurement**: - A commonly used research metric that allows for **quantifiable impact assessment**. \
                3. **Description**: A short explanation of **what happens if electric vehicles do not exist**. \
                4. **Expected Impact**: \
                - A measurable **difference in impact** compared to the original intervention. \
                - Where possible, **include numerical estimates, percentage changes, or relative comparisons**. \
                5. **Relevant Data Points**: \
                - Provide **supporting research, statistics, or calculations** from credible sources. \
                - If exact data is unavailable, suggest **alternative indicators or modeling approaches**. \
                ### **External Research & Sources**: \
                - Search the **internet**, **research databases**, **government reports**, and **news sources** to gather evidence. \
                - Include **at least 5 reputable sources** with **inline citations** (e.g., `[1]`) and a **bibliography** at the end. \
                - Prefer sources from **peer-reviewed journals (e.g., ScienceDirect, ArXiv, PubMed)**, **official government sites (e.g., EPA, WHO, UN reports)**, and **trusted media outlets (e.g., NYTimes, BBC, Forbes)**. \
                At the end, list the sources used with citation"
        # Call Perplexity API to generate counterfactuals
        response_text = call_perplexity([
            {"role": "system", "content": f"Generate two counterfactuals based on the given company website text. The standard is {counterfac_exp}"},
            {"role": "user", "content": self.website_data}
        ])

        shared_memory["counterfactual_scenarios"] = response_text
        return {
            "role": "assistant",
            "content": f"Top counterfactuals:\n{response_text}"
        }

class BaselineResearchAgent(autogen.AssistantAgent):
    def __init__(self, name, data, **kwargs):
        super().__init__(name=name, **kwargs)  # Pass 'name' to superclass AssistantAgent
        self.counterfactual_scenarios = data  # Store extracted counterfactual data
    
    def generate_reply(self, messages, sender, **kwargs):
        """Conducts baseline research to establish a reference point for impact measurement."""

        if not self.counterfactual_scenarios:
            return {"role": "assistant", "content": "Error: No counterfactual scenarios provided for baseline research."}

        # Prompt for conducting baseline research
        baseline_prompt = "Conduct a **baseline research analysis** based on the following counterfactual scenarios. \
        Identify **industry benchmarks, government statistics, or academic research** that establish a **quantifiable baseline** \
        for comparison with First and Second Order Outcomes. \
        \
        ### **Baseline Research Requirements**: \
        - **Find reliable industry reports, peer-reviewed papers, and government data**. \
        - **Extract quantifiable metrics** (e.g., 'CO₂ emissions before EV adoption = 300g/km'). \
        - **Ensure data is recent and relevant** (preferably within the last 5 years). \
        \
        ### **Output Format:** \
        ``` \
        **Baseline Metric Name**: [Metric]  \
        **Unit**: [Measurement Unit]  \
        **Baseline Value**: [Value]  \
        ``` \
        \
        At the end, list the sources used with citation\
        Now, research and establish baseline metrics for the following counterfactual scenarios."

        # Call Perplexity AI to conduct baseline research
        response_text = call_perplexity([
            {"role": "system", "content": baseline_prompt},
            {"role": "user", "content": self.counterfactual_scenarios}
        ])

        # Store baseline data
        shared_memory["baseline_research"] = response_text

        return {
            "role": "assistant",
            "content": f"**Baseline Research Findings:**\n{response_text}",
            "data": {"baseline_research": response_text}
        }
class FirstOrderOutcomeAgent(autogen.AssistantAgent):
    def __init__(self, name, data, **kwargs):
        super().__init__(name=name, **kwargs)
        self.counterfactual_scenarios = data["counterfactual_scenarios"]
        self.baseline_research = data["baseline_research"]

    def generate_reply(self, messages, sender, **kwargs):
        """Generates First Order Outcomes with quantifiable, measurable impact."""

        if not self.counterfactual_scenarios or not self.baseline_research:
            return {"role": "assistant", "content": "Error: Missing counterfactual scenarios or baseline research."}

        # Improved Prompt for First Order Outcomes
        first_order_prompt = (
            "Analyze the following counterfactual scenarios and baseline research data to generate **First Order Outcomes**.\n"
            "- **First Order Outcome** must be the **direct, immediate effect** of the metric being implemented.\n"
            "- It should **quantify the difference** in impact **compared to the baseline value**.\n"
            "- The value **must be numerical and measurable in the same unit as the baseline metric**.\n"
            "- Use a format that includes the **exact percentage, amount, or impact value**.\n\n"
            "### **Output Format:**\n"
            "``` \n"
            "**First Order Outcome**: [Outcome Name] ([Unit], Change from Baseline)\n"
            "```\n\n"
            "At the end, list the sources used with citation"
            "Now, generate First Order Outcomes using the given counterfactual scenarios and baseline data."
        )

        # Call Perplexity AI for First Order Outcomes
        response_text = call_perplexity([
            {"role": "system", "content": first_order_prompt},
            {"role": "user", "content": f"Counterfactuals:\n{self.counterfactual_scenarios}\n\nBaseline Research:\n{self.baseline_research}"}
        ])

        # Store first-order outcomes
        shared_memory["first_order_outcomes"] = response_text

        return {
            "role": "assistant",
            "content": f"**First Order Outcomes:**\n{response_text}",
            "data": {"first_order_outcomes": response_text}
        }
    
class SecondOrderOutcomeAgent(autogen.AssistantAgent):
    def __init__(self, name, data, **kwargs):
        super().__init__(name=name, **kwargs)
        self.first_order_outcomes = data["first_order_outcomes"]

    def generate_reply(self, messages, sender, **kwargs):
        """Generates Second Order Outcomes with measurable, unique impacts."""

        if not self.first_order_outcomes:
            return {"role": "assistant", "content": "Error: No First Order Outcomes provided."}

        # Improved Prompt for Second Order Outcomes
        second_order_prompt = (
            "Analyze the following **First Order Outcomes** and generate **Second Order Outcomes** that are:\n"
            "- A **direct, measurable** consequence of the First Order Outcome.\n"
            "- Must be **unique** and **not just a repetition** of the First Order Outcome.\n"
            "- Must be **numerically quantifiable** and use **a measurable unit**.\n"
            "- Include the **exact change** in value or percentage from the First Order Outcome.\n\n"
            "### **Output Format:**\n"
            "``` \n"
            "**Second Order Outcome**: [Outcome Name] ([Unit], Change from First Order Outcome)\n"
            "```\n\n"
            "At the end, list the sources used with citation"
            "Now, generate the Second Order Outcomes based on the following First Order Outcomes."
        )

        # Call Perplexity AI for Second Order Outcomes
        response_text = call_perplexity([
            {"role": "system", "content": second_order_prompt},
            {"role": "user", "content": self.first_order_outcomes}
        ])

        # Store second-order outcomes
        shared_memory["second_order_outcomes"] = response_text

        return {
            "role": "assistant",
            "content": f"**Second Order Outcomes:**\n{response_text}",
            "data": {"second_order_outcomes": response_text}
        }
    
class FinalSummaryAgent(autogen.AssistantAgent):
    def __init__(self, name, data, **kwargs):
        super().__init__(name=name, **kwargs)
        self.shared_memory = data  # Access all collected data

    def generate_reply(self, messages, sender, **kwargs):
        """Validates and summarizes all collected impact data into a structured report."""

        # Check if all required data is available
        if not all(key in self.shared_memory for key in ["counterfactual_scenarios", "baseline_research", "first_order_outcomes", "second_order_outcomes"]):
            return {"role": "assistant", "content": "Error: Missing required data for final summary."}

        # Extract relevant data
        counterfactual_scenarios = self.shared_memory["counterfactual_scenarios"]
        baseline_research = self.shared_memory["baseline_research"]
        first_order_outcomes = self.shared_memory["first_order_outcomes"]
        second_order_outcomes = self.shared_memory["second_order_outcomes"]

        # Final Summary Prompt
        summary_prompt = (
            "Generate a **structured impact summary** using the validated data from counterfactual scenarios, "
            "baseline research, first-order outcomes, and second-order outcomes. "
            "Ensure all information is **quantifiable, logically consistent, and aligned with industry standards**.\n\n"
            "### **Final Summary Report Structure**:\n"
            "- **Counterfactual Analysis**: Summarize the key counterfactuals analyzed.\n"
            "- **Baseline Research**: Report industry-standard benchmarks used for comparison.\n"
            "- **First Order Outcomes**: List and validate the immediate effects of implementing the intervention.\n"
            "- **Second Order Outcomes**: Summarize indirect ripple effects and ensure they are distinct from First Order Outcomes.\n"
            "- **Overall Impact Assessment**: Provide a conclusion based on the **net quantified impact**.\n"
            "- **Validation Check**: Ensure all figures align with industry benchmarks and sources are properly cited.\n\n"
            "### **Output Format:**\n"
            "```\n"
            "**Counterfactual Analysis**:\n"
            "[Concise summary of counterfactuals]\n\n"
            "**Baseline Research**:\n"
            "[Key baseline metrics used for comparison]\n\n"
            "**First Order Outcomes**:\n"
            "- [Outcome Name] ([Unit], Change from Baseline)\n"
            "- [Outcome Name] ([Unit], Change from Baseline)\n\n"
            "**Second Order Outcomes**:\n"
            "- [Outcome Name] ([Unit], Change from First Order Outcome)\n"
            "- [Outcome Name] ([Unit], Change from First Order Outcome)\n\n"
            "**Overall Impact Assessment**:\n"
            "[Summarize net effect with quantifiable insights]\n\n"
            "**Validation Check**:\n"
            "[Ensure all figures align with industry benchmarks]\n"
            "```\n\n"
            "Now, summarize the collected data into the required format."
        )

        # Call Perplexity AI to validate & summarize
        response_text = call_perplexity([
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": f"Counterfactuals:\n{counterfactual_scenarios}\n\nBaseline Research:\n{baseline_research}\n\nFirst Order Outcomes:\n{first_order_outcomes}\n\nSecond Order Outcomes:\n{second_order_outcomes}"}
        ])

        # Store final summary
        shared_memory["final_summary"] = response_text

        return {
            "role": "assistant",
            "content": f"**Final Validated Summary:**\n{response_text}",
            "data": {"final_summary": response_text}
        }

# Citation Validation Agent
class CitationValidationAgent(autogen.AssistantAgent):
    def generate_reply(self, messages, sender, **kwargs):
        """Verifies the validity of the data sources."""
        response_text = call_perplexity(messages)
        return {"role": "assistant", "content": f"Verified citations:\n{response_text}"}


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

    # Step 1: Extract website data
    website_parsing_agent = WebsiteParsingAgent(name="WebsiteParsingAgent")
    website_task = "Provide a website URL for counterfactual analysis."
    user_proxy.initiate_chat(website_parsing_agent, message=website_task)

    # Step 2: Generate counterfactual scenarios
    scenario_agent = ScenarioIdentificationAgent(name="ScenarioIdentificationAgent", data=shared_memory["website_text"])
    user_proxy.initiate_chat(scenario_agent, message="Generate counterfactual scenarios.")

    # Step 3: Conduct Baseline Research
    baseline_agent = BaselineResearchAgent(name="BaselineResearchAgent", data=shared_memory["counterfactual_scenarios"])
    user_proxy.initiate_chat(baseline_agent, message="Conduct baseline research.")

    # Step 4-5: Generate First and Second Order Outcomes
    first_order_agent = FirstOrderOutcomeAgent(name="FirstOrderOutcomeAgent", data=shared_memory)
    user_proxy.initiate_chat(first_order_agent, message="Identify First Order Outcomes.")

    second_order_agent = SecondOrderOutcomeAgent(name="SecondOrderOutcomeAgent", data=shared_memory)
    user_proxy.initiate_chat(second_order_agent, message="Identify Second Order Outcomes.")

    # Step 6: Generate Final Validated Summary
    final_summary_agent = FinalSummaryAgent(name="FinalSummaryAgent", data=shared_memory)
    user_proxy.initiate_chat(final_summary_agent, message="Generate a validated impact summary.")


if __name__ == "__main__":
    main()
