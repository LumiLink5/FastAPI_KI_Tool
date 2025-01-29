import streamlit as st
import json
import requests

st.set_page_config(page_title="ProcurDat CPV Codes", layout="wide")

st.title("Common Procurement Vocabulary (CPV) Generierung")

left, right = st.columns([2, 2])

welcome_message = (
        "Willkommen zur Testanwendung für die automatische Generierung von CPV-Codes für Vergabe Ausschreibungen. "
        "Diese Anwendung wurde von Dataport in Zusammenarbeit mit der Universität Bremen entwickelt. " 
        "Ziel ist es, den Prozess der Codierung zu optimieren und effizienter zu gestalten. "
    )

left.write(welcome_message)

model = left.selectbox("Welches Model soll für die Vorhersage benutzt werden?", ("Großes Model", "Kleines Model"))

cpv_number = left.number_input('Wie viele CPV Nummern sollen generiert werden?', min_value=1, step=1, value=3)

sentence = left.text_area('Eingabe des Vergabe-Textes', 'Es sollen 3 Computer für ein Büro beschaffen werden.', height=550)

inputs = {"model_name": model, "k": cpv_number, "q": sentence}

left_1, mid_1, right_1 = left.columns(3)

container_right = right.container(height=1000, border=True)

if mid_1.button("CPV Nummern generieren", use_container_width=True):
    left_2, mid_2, right_2 = container_right.columns(3)
    placeholder = mid_2.empty()

    with placeholder, st.spinner('Passende CPV Nummern werden ermittelt...'):
        res = requests.post(url="http://127.0.0.1:8000/cpv", data=json.dumps(inputs))

    response_data = res.json()

    for idx, item in enumerate(response_data['vorhergesagte_bezeichnung']):
        cpv_number = item[1]
        cpv_bezeichnung = item[0]
        cpv_ergenzung = item[2]
        cpv_percent = item[3]

        container = container_right.container(border=True)

        subheader, percentage = container.columns((8,1))

        # Display the CPV information
        subheader.subheader(f"CPV Nummer: {cpv_number}")

        percentage.subheader(f"{cpv_percent}")

        container.write(f"{cpv_bezeichnung}")

        if cpv_ergenzung:
            container.info(f'{cpv_ergenzung}', icon="ℹ️")

        with container.expander(label="Zugehörige Gruppen"):
            response = requests.post(url=f"http://127.0.0.1:8000/cpv_groups?cpv_number={cpv_number}")
            response_data = response.json()
            
            for item in response_data:
                st.write(f"**{item[0]}** ({item[1]})")



end_message = (
        "Beide Modelle wurden auf denselben Datensätzen trainiert und basieren ausschließlich auf der obersten Ebene der CPV-Nummern (den Divisions). " 
        "Eine detailliertere Betrachtung der hierarchischen Struktur der CPV-Nummern wurde bisher nicht vorgenommen. " 
        "Bei dem Projekt beteiligt sind: Gerhard Klaasen, Robin Fritzsche, Marco Kruse, Andrey Krutilin, Benjamin Haberkorn, Tetiana Prykhodko. " 
        "Bei Fragen sprechen Sie uns gerne an!"
    )

left.write(end_message)