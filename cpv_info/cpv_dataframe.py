import PyPDF2
import pandas as pd
import re

# HOW TO USE 
# result_df = process_files('path_to_excel, 'path_to_pdf')

def extract_codes(df, code_column):
    def get_division(code):
        return code[:2]

    def get_group(code):
        return code[:3]

    def get_class(code):
        return code[:4]

    def get_category(code):
        return code[:5]

    def get_classification(code):
        code = code.split('-')[0]
        if code.endswith('000000'):
            return 'division'
        elif code.endswith('00000'):
            return 'group'
        elif code.endswith('0000'):
            return 'class'
        elif code.endswith('000'):
            return 'category'
        else:
            return 'subclass'

    df['division'] = df[code_column].apply(get_division)
    df['group'] = df[code_column].apply(get_group)
    df['class'] = df[code_column].apply(get_class)
    df['category'] = df[code_column].apply(get_category)
    df['classification'] = df[code_column].apply(get_classification)

    return df

def extract_abteilung_sections(text):
    pattern = r'(ABTEILUNG \d+:.*?)(?=ABTEILUNG \d+:|$)'
    return re.findall(pattern, text, re.DOTALL | re.MULTILINE)

def extract_abteilung_gruppe_patterns(strings):
    pattern = r"ABTEILUNG.*?(?=Gruppe \d{3}:)"
    results = []
    for text in strings:
        matches = re.findall(pattern, text, re.DOTALL)
        results.append(matches if matches else [text])
    return results

def extract_gruppe_blocks(strings):
    pattern = r"(?<!gehören zu\s)Gruppe\s*\d{3}:.*?(?=(?<!gehören zu\s)Gruppe\s*\d{3}:|$)"
    results = []
    for text in strings:
        matches = re.findall(pattern, text, re.DOTALL)
        results.append(matches)
    return results

def extract_groups_and_classes(strings):
    group_pattern = r'(Gruppe \d{3}:.*?)(?=Gruppe \d{3}:|Klasse \d{4}|$)'
    extracted_groups = []
    remaining_classes = []

    for text in strings:
        groups = re.findall(group_pattern, text, re.DOTALL)
        extracted_groups.append([group.strip() for group in groups])
        remaining_text = re.sub(group_pattern, '', text, flags=re.DOTALL).strip()
        remaining_classes.append(remaining_text)

    flattened_groups = [group for sublist in extracted_groups for group in sublist]
    return flattened_groups, remaining_classes

def separate_classes(strings):
    pattern = r'(Klasse \d{4}:.*?)(?=Klasse \d{4}:|$)'
    separated_classes = []
    for text in strings:
        matches = re.findall(pattern, text, re.DOTALL)
        separated_classes.extend([match.strip() for match in matches])
    return separated_classes

def extract_classes(strings):
    pattern = r'(Klasse \d{4}:.*?)(?=Klasse \d{4}:|$)'
    extracted_classes = []
    for text in strings:
        matches = re.findall(pattern, text, re.DOTALL)
        extracted_classes.extend([match.strip() for match in matches])
    return extracted_classes

def match_cpv_numbers(row, combi):
    if row["classification"] == "division":
        search_number = row["division"]
        search_prefix = f"ABTEILUNG {search_number}:"
    elif row["classification"] == "group":
        search_number = row["group"]
        search_prefix = f"Gruppe {search_number}:"
    elif row["classification"] == "class":
        search_number = row["class"]
        search_prefix = f"Klasse {search_number}:"
    else:
        return None

    for entry in combi:
        if entry.startswith(search_prefix):
            match = re.search(rf"{re.escape(search_prefix)}\s*(.*)", entry)
            return match.group(1).strip() if match else entry
    return None

def remove_initial_all_caps(text):
    if not isinstance(text, str):
        return text
    words = text.split()
    for i, word in enumerate(words):
        if not word.isupper():
            return ' '.join(words[i:])
    return ''

def process_files(excel_path, pdf_path):
    cvp_numbers = pd.read_excel(excel_path, usecols=['CODE', 'DE'])
    df = extract_codes(cvp_numbers, 'CODE')

    combined_text = ""
    with open(pdf_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            combined_text += page.extract_text()

    list_of_abteilungen = extract_abteilung_sections(combined_text)
    abteilungen = extract_abteilung_gruppe_patterns(list_of_abteilungen)
    list_of_gruppen = extract_gruppe_blocks(list_of_abteilungen)
    list_of_gruppen = [item for i in list_of_gruppen for item in i]
    list_of_abteilungen_2 = [item for i in abteilungen for item in i]
    just_gruppen, just_klassen = extract_groups_and_classes(list_of_gruppen)
    just_klassen_separated = separate_classes(just_klassen)
    combi = list_of_abteilungen_2 + just_gruppen + just_klassen_separated

    df["description"] = df.apply(lambda row: match_cpv_numbers(row, combi), axis=1)
    df["description"] = df["description"].apply(remove_initial_all_caps)

    return df


