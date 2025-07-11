from openai import OpenAI
import ast
from config import OPENAI_API_KEY
from config import THESIS
import pandas as pd


client = OpenAI(api_key=OPENAI_API_KEY)
def create_batch_prompt(deals: str,climate_only = False) -> str:
    if climate_only:
        prompt = f"""
    You are a structured data extractor for venture deals. Below are multiple deal descriptions. 

    For each, extract the following 7 fields and return a Python list of lists (one list per deal), with **no explanations**:

    1. Company Name
    2. Deal Size (e.g., "$87M")
    3. Funding Series (e.g., "Seed", "Series A", "Growth", "Post-IPO Equity", etc.), If the series cannot be found leave it as an empty string.
    4. Tagline – a short phrase describing what the company does
    5. Headquarters Location (e.g., "City, Country" or "City, State")
    6. Lead Investors – names separated by commas
    7. Using the company name, location, and tagline, determine its website domain by performing a google search. If the domain cannot be found, 
    then leave as an empty string, but try as hard as possible to find the domain.
    Do not forget about any of these categories. 
    Make sure that the inner lists have exactly 7 elements
    💡 Ignore any emojis and any symbol mistakes like ~__----///. Maintain original capitalization and punctuation.
    DO NOT 
    ### Format:

    [
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain"],
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain"],

    ...
    ]
    ### Example
    For instance if the input was: 
    ⚡ SkyNRG, an Amsterdam, Netherlands-based sustainable aviation fuel producer, raised $284m in Growth funding from APG Asset Management. 

    ⚡ Radiant Nuclear, an El Segundo, CA-based micro nuclear reactor developer, raised $165m in Series C funding from DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital, and other investors.

    ⚡ Battery Smart, a Gurgaon, India-based battery swapping network service, raised $29m in Series B funding from Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, and responsAbility Investments. 

    🏭 ecop, a Vienna, Austria-based high-tech heat pump manufacturer, raised $12m in Growth funding from European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, and New Energy Technology (AUS). 

    Early-Stage
    ⚡ Heron Power, a Santa Cruz, CA-based power electronics manufacturer, raised $38m in Series A funding from Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures, and other investors. 

    🏠 Gridcare, a Redwood City, CA-based grid investment optimization platform, raised $14m in Seed funding from Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures, and other investors. 
    and your output should be:
    [
        ["SkyNRG", "$284M", "Growth", "Sustainable aviation fuel producer", "Amsterdam, Netherlands", "APG Asset Management","https://skynrg.com/"],

        ["Radiant Nuclear", "$165M", "Series C", "Micro nuclear reactor developer", "El Segundo, CA", "DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital","https://www.radiantnuclear.com/"],

        ["Battery Smart", "$29M", "Series B", "Battery swapping network service", "Gurgaon, India", "Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, responsAbility Investments"in","https://www.batterysmart.in/"],

        ["ecop", "$12M", "Growth", "High-tech heat pump manufacturer", "Vienna, Austria", "European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, New Energy Technology (AUS)","https://www.ecop.at/"],

        ["Heron Power", "$38M", "Series A", "Power electronics manufacturer", "Santa Cruz, CA", "Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures", "https://www.heronpower.com/" ],

        ["Gridcare", "$14M", "Seed", "Grid investment optimization platform", "Redwood City, CA", "Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures","https://www.gridcare.ai/"],

    ]
        ### Task
        Now perform this operation for the following input: {deals}
        The final output should be a list of lists
        """
    else:
        prompt = f"""
    You are a structured data extractor for venture deals. Below are multiple deal descriptions. 

    For each, extract the following 7 fields and return a Python list of lists (one list per deal), with **no explanations**:

    1. **Company Name**
    2. **Deal Size** – e.g., "$87M"
    3. **Funding Series** – e.g., "Seed", "Series A", "Growth", "Post-IPO Equity", etc.
    4. **Tagline** – a short phrase describing what the company does
    5. **Headquarters Location** – formatted as "City, Country" or "City, State"
    6. **Lead Investors** – names separated by commas
    7. **Company Website Domain** – using the company name, location, and tagline, find the official website via Google search; if unavailable, return an empty string
    8. **In Thesis** – Boolean `True` or `False` indicating whether the company fits the following investment thesis:{THESIS}

    > The company should be **asset-light**, primarily **software-based** (but light hardware components are allowed), and focused on enabling the **energy transition**, **sustainability**, **resilience**, **rare earths**, **electrification**, **autonomy**, **digitization**,**infrastructure**,**permitting**.
    > Do **not** include companies operating solely in **finance**, **hospitality**, **customer service**, **blockchain**, **health**, **hiring/employment**, **Marketing**, or other areas unrelated to climate or sustainability.

    ### Format:

    [
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain", In thesis],
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain", In thesis],

    ...
    ]
    ### Example
    For instance if the input was: 
    ⚡ SkyNRG, an Amsterdam, Netherlands-based sustainable aviation fuel producer, raised $284m in Growth funding from APG Asset Management. 

    ⚡ Radiant Nuclear, an El Segundo, CA-based micro nuclear reactor developer, raised $165m in Series C funding from DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital, and other investors.

    ⚡ Battery Smart, a Gurgaon, India-based battery swapping network service, raised $29m in Series B funding from Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, and responsAbility Investments. 

    🏭 ecop, a Vienna, Austria-based high-tech heat pump manufacturer, raised $12m in Growth funding from European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, and New Energy Technology (AUS). 
    Paraform, $4m, Seed, Connect startupts with recruiter networks, Software, Mayfield
    Early-Stage
    ⚡ Heron Power, a Santa Cruz, CA-based power electronics manufacturer, raised $38m in Series A funding from Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures, and other investors. 

    🏠 Gridcare, a Redwood City, CA-based grid investment optimization platform, raised $14m in Seed funding from Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures, and other investors. 
    and your output should be:
    [
        ["SkyNRG", "$284M", "Growth", "Sustainable aviation fuel producer", "Amsterdam, Netherlands", "APG Asset Management","https://skynrg.com/"],

        ["Radiant Nuclear", "$165M", "Series C", "Micro nuclear reactor developer", "El Segundo, CA", "DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital","https://www.radiantnuclear.com/", True],

        ["Battery Smart", "$29M", "Series B", "Battery swapping network service", "Gurgaon, India", "Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, responsAbility Investments"in","https://www.batterysmart.in/", True],

        ["ecop", "$12M", "Growth", "High-tech heat pump manufacturer", "Vienna, Austria", "European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, New Energy Technology (AUS)","https://www.ecop.at/",True],

        ["Heron Power", "$38M", "Series A", "Power electronics manufacturer", "Santa Cruz, CA", "Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures", "https://www.heronpower.com/",True ],

        ["Gridcare", "$14M", "Seed", "Grid investment optimization platform", "Redwood City, CA", "Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures","https://www.gridcare.ai/",True],

        ["Paraform", "$4m", "Seed", "Connect startupts with recruiter networks", " ", "Mayfield","https://www.paraform.com/", False]
]
    ]
        ### Task
        Now perform this operation for the following input: {deals}
        The final output should be a list of lists
        """
       
    return prompt

def classify_industry(text,climate_only = False):
    prompt = create_batch_prompt(text,climate_only)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Model specification
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    result = completion.choices[0].message.content
    try:
        result = ast.literal_eval(result)
    except Exception:
        result = "["+result+"]"
        result = ast.literal_eval(result)

    return result

def filter(list_of_lists):
    filter_data =[]
    for i in list_of_lists:
        if i[-1]:
            filter_data.append(i[:-1])
    return filter_data

def dataframe_OPENAI(text: str,climate_only=False) -> pd.DataFrame:
    # deals = strip_deal_sections(text)

    def try_classify_once():
        try:
            result = classify_industry(text,climate_only)
            if not climate_only:
                result = filter(result)
            if not isinstance(result, list) or not all(len(item) == 7 for item in result):
                raise ValueError("Invalid result structure")
            return result
        except Exception as e:
            print(f"Classification error: {e}")
            return None

    # First attempt
    categorized_list = try_classify_once()
    # Retry once if failed
    if not categorized_list:
        print("Retrying classify_industry...")
        categorized_list = try_classify_once()

    # Build dataframe if successful
    if categorized_list:
        columns = [
            "Company", "Deal Size", "Series", "Tagline", "Location", "Lead Investors", "domain"
        ]
        return pd.DataFrame(categorized_list, columns=columns)
    else:
        print("Couldn't extract")
    
    return None


from bs4 import BeautifulSoup

def ctvc(html):
    pass

def keepcool(html):
    pass

def fortune(html):
    pass

def european_substack(html):
    pass

def general_text_parser(html):
    soup = BeautifulSoup(html,"html.parser")
    return soup.get_text()

def split_df(df):
    companies_df = df[["Company", "Tagline", "Location", "Domain"]]
    deals_df = df[["Comapany","Series","Lead Investor","Date","Source"]]