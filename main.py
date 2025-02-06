import sys
from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException
from huggingface_hub import hf_hub_download
import fasttext
from setfit import SetFitModel
import pandas as pd
import numpy as np


sys.path.append('cpv_info/')
import cpv_dataframe

ft_repo_id = "tanjapry/fasttext_42l_117e_title_description"
ft_model_path = hf_hub_download(repo_id=ft_repo_id, filename="model.bin")
fasttext_model = fasttext.load_model(ft_model_path)

sf_model_id = "tanjapry/setfit_ausschreibung"
setfit_model = SetFitModel.from_pretrained(sf_model_id)


CPV_DIR = "cpv.json"
cpv_numbers = pd.read_json(CPV_DIR)

app = FastAPI()

class ModelName(str, Enum):
    fasttext = "Großes Model"
    setfit = "Kleines Model"

class User_input(BaseModel):
    model_name : ModelName
    #k : int
    q : str

@app.post("/cpv")
async def read_items(input:User_input):
    global fasttext_model, setfit_model

    print(input.q)

    #min_percent = f"0.{input.k}"
    #min_percent = float(min_percent)
    min_percent = 0.01

    if input.model_name is ModelName.setfit:
        if setfit_model is None:
            raise HTTPException(status_code=500, detail="SetFit model not loaded")
        proba = setfit_model.predict_proba(input.q)
        proba_np = proba.numpy()

        filtered_indices = np.where(proba_np > min_percent)[0]  
        filtered_labels = [setfit_model.labels[i] for i in filtered_indices]
        filtered_probabilities = proba_np[filtered_indices]
        filtered_percentages = [f"{round(prob * 100)}%" for prob in filtered_probabilities]


    elif input.model_name == ModelName.fasttext:
        if fasttext_model is None:
            raise HTTPException(status_code=500, detail="FastText model not loaded")
        predictions = fasttext_model.predict(input.q, k=-1)  # k=-1 to get predictions for all labels
        all_labels = predictions[0]
        all_probabilities = predictions[1]
        
        filtered_indices = [i for i, prob in enumerate(all_probabilities) if prob > min_percent]
        filtered_labels = [all_labels[i].replace('__label__', '') for i in filtered_indices]
        filtered_probabilities = [all_probabilities[i] for i in filtered_indices]
        filtered_percentages = [f"{round(prob * 100)}%" for prob in filtered_probabilities]


    print(filtered_labels)

    bezeichnung_list = []

    for label in filtered_labels:
        bezeichnung = cpv_numbers[(cpv_numbers["classification"] == "division") & 
                                        (cpv_numbers["division"] == int(label))]["DE"].values[0]
        bezeichnung_list.append(bezeichnung)

    cpv_list = []

    for label in filtered_labels:
        bezeichnung = cpv_numbers[(cpv_numbers["classification"] == "division") & 
                                        (cpv_numbers["division"] == int(label))]["CODE"].values[0]
        cpv_list.append(bezeichnung)

    result_df = cpv_dataframe.process_files("cpv_info/cpv_2008_ver_2013.xlsx", "cpv_info/cpv_2008_explanatory_notes_de.pdf")

    cpv_description_list = []

    for label in filtered_labels:
        label_description = result_df[(result_df["classification"] == "division") & (result_df["division"] == label)]["description"].values[0]
        cpv_description_list.append(label_description)

    top_k_predictions = list(zip(bezeichnung_list, cpv_list, cpv_description_list, filtered_percentages))



    return {"model": input.model_name, "anfrage": input.q, "vorhergesagte_bezeichnung": top_k_predictions}

@app.post("/cpv_groups")
async def read_groups(cpv_number: str):
    group_list = []
    bezeichnung_list = []

    group_list = cpv_numbers[(cpv_numbers["classification"] == "group") & (cpv_numbers["division"] == int(str(cpv_number)[:2]))]["CODE"].tolist()
    
    bezeichnung_list = cpv_numbers[(cpv_numbers["classification"] == "group") & (cpv_numbers["division"] == int(str(cpv_number)[:2]))]["DE"].tolist()

    groups_descriptions = list(zip(group_list, bezeichnung_list))

    return groups_descriptions
