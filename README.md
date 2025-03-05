# Multi_Agent_Framework

The pipeline is built up in the app.py file

How to run and test the program:

1. Clone the repository 
2. Run by

```
python3 app.py
```
ensure that you've installed all the libraries at the top of app.py to successfully run the code, this is an example of installing autogen

```
pip install autogen
```

**Below includes the description of each agent and prompts fed into Perplexity**

General System Prompt:
You are an expert in Impact Analysis. Your ultimate task is to compile a list that \
includes metrics, counterfactuals, first-order outcomes, second-order outcomes, and costs that \
this company can directly measure. It is crucial that metrics, counterfactuals, first-order outcomes,\
second-order outcomes, and costs are quantifiable. \Each output must:\
1. **Include Quantifiable Metrics** - Ensure that all values provided are measurable and align with real-world impact frameworks.\
2. **Assess Counterfactuals** - Identify and validate alternative scenarios to provide comparative insights.\
3. **Evaluate Outcomes** - Distinguish between first-order (direct) and second-order (indirect) outcomes.\
4. **Validate Research & Sources** - Pull relevant research, verify citations, and cross-check for hallucinations or inconsistencies.\
5. **Align with Impact Standards** - Ensure outputs align with relevant sustainability and impact measurement frameworks such as SDGs, IRIS+, and others.",
       

# Agents

## 1. WebsiteParsingAgent - parse the website and return a summary of information

## 2. ScenarioIdentificaitonAgent - Identify 2 Counterfactual scenario

Prompt: "Conduct an **internet-wide search**, including academic papers, government reports, and industry sources, to generate a          structured list of counterfactual scenarios analyzing alternative outcomes in the absence of company's product or service. \
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


## 3. Baseline Research on the total size of the problem
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



## 4. First-Order Agent
based upon scenario identification agent and baseline research agent

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


## 5. Second-Order Agent
based upon information from baseline research and first-order agents

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

## 6. Validate all the information; Summary of the research pulled together

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
