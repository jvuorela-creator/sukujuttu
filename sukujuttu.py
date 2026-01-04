import streamlit as st
from audio_recorder_streamlit import audio_recorder
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload # Käytämme vain tätä
import os
import datetime
import random

# --- ASETUKSET ---
st.set_page_config(page_title="Sukumuistot v4.0", page_icon="💾")

TARGET_FOLDER_NAME = "Sukumuistot"

KYSYMYKSET = [
    "Kuka oli paras ystäväsi lapsuudessa?",
    "Mitä söitte jouluna, kun olit pieni?",
    "Kerro ensimmäisestä koulupäivästäsi.",
    "Millainen oli isäsi/äitisi luonne?",
    "Mikä on ollut elämäsi onnellisin hetki?",
]

# --- GOOGLE DRIVE -YHTEYDET ---

def get_drive_service():
    creds_dict = dict(st.secrets)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def get_folder_id(service, folder_name):
    results = service.files().list(
        q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'",
        fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        return None
    return items[0]['id']

def save_to_drive(audio_bytes, filename):
    try:
        service = get_drive_service()
        folder_id = get_folder_id(service, TARGET_FOLDER_NAME)

        if not folder_id:
            st.error(f"Kansiota '{TARGET_FOLDER_NAME}' ei löytynyt!")
            return False
        
        # --- RAUTALANKA-RATKAISU: Tallennus levylle ---
        # 1. Tallennetaan ääni väliaikaisesti palvelimen levylle
        temp_filename = "temp_upload.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
            
        # 2. Lähetetään tiedosto levyltä (MediaFileUpload toimii varmasti)
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaFileUpload(temp_filename, mimetype='audio/wav')
        
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # 3. Siivotaan jäljet (poistetaan temp-tiedosto)
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return True

    except Exception as e:
        st.error(f"Virhe tallennuksessa: {e}")
        return False

def list_and_play_files():
    try:
        service = get_drive_service()
        folder_id = get_folder_id(service, TARGET_FOLDER_NAME)
        
        if not folder_id:
            return

        # Haetaan lista
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
            orderBy="createdTime desc",
            pageSize=5,
            fields="files(id, name)").execute()
        
        items = results.get('files', [])

        if not items:
            st.info("Ei vielä tallennettuja muistoja.")
            return

        st.subheader("🎧 Kuuntele uusimmat muistot")
        
        for item in items:
            with st.expander(f"📁 {item['name']}"):
                try:
                    # --- RAUTALANKA-RATKAISU: Lataus ---
                    # Ei käytetä MediaIoBaseDownloadia, vaan haetaan raaka data execute():lla
                    file_content = service.files().get_media(fileId=item['id']).execute()
                    
                    # file_content on nyt suoraan 'bytes', jonka st.audio ymmärtää
                    st.audio(file_content, format="audio/wav")
                    
                except Exception as e:
                    st.warning(f"Virhe toistossa: {e}")

    except Exception as e:
        st.error(f"Virhe listan haussa: {e}")

# --- KÄYTTÖLIITTYMÄ ---

st.markdown("<h1 style='text-align: center; color: #d9455f;'>💾 Sukumuistot v4.0</h1>", unsafe_allow_html=True)

if 'current_question' not in st.session_state:
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

if st.button("🔄 Vaihda kysymys"):
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

st.info(f"Kysymys: {st.session_state['current_question']}")

# --- NAUHOITUS ---
wav_audio_data = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x",
)

if wav_audio_data is not None:
    st.audio(wav_audio_data, format='audio/wav')
    puhuja = st.text_input("Kuka puhuu?", placeholder="Nimi")
    
    if st.button("TALLENNA PILVEEN"):
        if not puhuja:
            st.warning("Kerro ensin kuka puhuu.")
        else:
            with st.spinner("Tallennetaan..."):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
                clean_name = "".join(x for x in puhuja if x.isalnum())
                clean_q = st.session_state['current_question'][:10].replace(" ","_")
                filename = f"{timestamp}_{clean_name}_{clean_q}.wav"
                
                if save_to_drive(wav_audio_data, filename):
                    st.success("Tallennettu!")
                    import time
                    time.sleep(1)
                    st.rerun()

st.divider()
list_and_play_files()
