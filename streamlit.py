import streamlit as st
import json
import requests
import streamlit_analytics
import clipboard

def on_copy_click(text, idx):
    st.session_state.copied.append(text)
    clipboard.copy(text)
    st.session_state[f"copied_{idx}"] = True

st.set_page_config(page_title="ProcurDat CPV Codes", layout="wide")

st.markdown(
    """
    <style>
        /* Change the base font size for the whole app */
        :root {
            font-size: 18px !important; /* Adjust this value as needed */
        }

        /* Override Streamlit's default text styling */
        html, body, [class*="st-"] {
            font-size: 18px !important;
        }

        /* Customize button font size */
        button {
            font-size: 16px !important;
        }

        /* Customize sidebar font */
        [data-testid="stSidebar"] {
            font-size: 16px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)


st.title("Common Procurement Vocabulary (CPV) Navigator")

left, right = st.columns([2, 2])

welcome_message = (
        "Willkommen zur Testanwendung für die automatische Zuordnung von CPV-Codes für Vergabeverfahren. Diese Anwendung wurde von Dataport in Zusammenarbeit mit der Universität Bremen entwickelt. Bitte wählen Sie eines der beiden verfügbaren Modelle aus und geben Sie einen eigenen Text ein, für den die entsprechenden CPV-Codes ermittelt werden."
    )

left.write(welcome_message)

model = left.selectbox("Welches Model soll für die Vorhersage benutzt werden?", ("Großes Model", "Kleines Model"))

#percentage_min = left.number_input('Ab wie vielen Prozent sollen CPV Codes angezeigt werden?', min_value=1, step=1, value=10)

sentence = left.text_area('Eingabe des Vergabe-Textes', 'Es sollen 3 Computer für ein Büro beschaffen werden.', height=410)

sentence = sentence.replace("\n", " ")

inputs = {"model_name": model,  "q": sentence}

left_1, mid_1, right_1 = left.columns(3)

container_right = right.container(height=1000, border=True)

if "copied" not in st.session_state: 
    st.session_state.copied = []
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "results_data" not in st.session_state:
    st.session_state.results_data = None

if mid_1.button("CPV Nummern ermitteln", use_container_width=True):
    container_right.empty()
    st.session_state.results_data = None
    left_2, mid_2, right_2 = container_right.columns(3)
    placeholder = mid_2.empty()

    st.session_state.show_results = False  
    with placeholder, st.spinner('Passende CPV Nummern werden ermittelt...'):
        res = requests.post(url="http://127.0.0.1:8000/cpv", data=json.dumps(inputs))

    st.session_state.results_data = res.json()
    st.session_state.show_results = True  

if st.session_state.show_results:

    for idx, item in enumerate(st.session_state.results_data['vorhergesagte_bezeichnung']):
        cpv_number = item[1]
        cpv_bezeichnung = item[0]
        cpv_ergenzung = item[2]
        cpv_percent = item[3]

        container = container_right.container(border=True)

        subheader, cpv, placeholder, percentage = container.columns((4, 1, 4, 1))

        # Display the CPV information
        subheader.subheader(f"CPV Nummer {cpv_number}")
        if cpv.button(label="", icon=":material/content_copy:", on_click=on_copy_click, args=(cpv_number, idx), key=f"button_{idx}"):
            st.session_state[f"copied_{idx}"] = True  # Store copy state for this CPV number
            st.toast(f"Copied to clipboard: {cpv_number}", icon='✅')

        #percentage.subheader(f"{cpv_percent}")

        container.write(f"{cpv_bezeichnung}")

        if cpv_ergenzung:
            container.info(f'{cpv_ergenzung}', icon="ℹ️")

        with container.expander(label="Zugehörige Gruppen"):
            response = requests.post(url=f"http://127.0.0.1:8000/cpv_groups?cpv_number={cpv_number}")
            response_data = response.json()
            
            for item in response_data:
                st.write(f"**{item[0]}** ({item[1]})")


left.subheader("FAQ:")

with left.expander(label="Was ist das große Modell?"):
    st.write("Das große Modell wurde auf 42 von insgesamt 45 vorhandenen CPV-Abteilungen trainiert. Dabei kamen sowohl die Titel als auch die Beschreibungen der Vergaben zum Einsatz. Für das Training wurden pro Abteilung 117 Einträge verwendet. Als Modell wurde FastText eingesetzt.")

with left.expander(label="Was ist das kleine Modell?"):
    st.write("Das kleine Modell wurde auf 23 von insgesamt 45 CPV-Abteilungen trainiert, wobei ausschließlich die Titel berücksichtigt wurden. Pro Vergabe wurden 300 Einträge für das Training genutzt. Hierbei kam das SetFit-Modell zum Einsatz.")

with left.expander(label="Welche Ebene der CPV-Nummern kann einer Vergabe zugeordnet werden?"):
    st.write("Bislang werden nur die Abteilung, also die oberste Ebene der CPV-Nummern zugewiesen. Es ist geplannt weitere KI-Modelle zu trainieren, so dass auch Gruppen und Klassen einer Text-Eingabe zugeordnet werden können.")
