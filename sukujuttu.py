import streamlit as st
from audio_recorder_streamlit import audio_recorder
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import datetime
import random

# --- VERSIOTARKISTUS ---
# Jos tämä otsikko ei näy sivulla, vanha koodi on yhä käynnissä!
st.set_page_config(page_title="Sukumuistot v2.0", page_icon="💾")

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
    # Haetaan tunnukset ja varmistetaan että ne ovat oikeassa muodossa
    creds_dict = dict(st.secrets)
    
    # Luodaan yhteys
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def get_folder_id(service, folder_name):
    # Etsii kansion ID:n
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
            st.error(f"Kansiota '{TARGET_FOLDER_NAME}' ei löytynyt! Tarkista nimeäminen.")
            return False
        
        # --- UUSI TAPA: Väliaikainen tiedosto ---
        # Tallennetaan ääni hetkeksi levylle, jotta Drive-kirjasto ei mene sekaisin
        temp_filename = "temp_upload.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
            
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaFileUpload(temp_filename, mimetype='audio/wav')
        
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # Siivotaan jäljet
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

        # Haetaan lista tiedostoista
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
            orderBy="createdTime desc",
            pageSize=5, # Näytetään aluksi vain 5 uusinta
            fields="files(id, name)").execute()
        
        items = results.get('files', [])

        if not items:
            st.info("Ei vielä tallennettuja muistoja.")
            return

        st.subheader("🎧 Kuuntele uusimmat muistot")
        
        for item in items:
            with st.expander(f"📁 {item['name']}"):
                try:
                    # Ladataan tiedoston sisältö suoraan muistiin (bytes)
                    # Tämä on yksinkertaisin tapa, joka ei vaadi striimausta
                    file_content = service.files().get_media(fileId=item['id']).execute()
                    st.audio(file_content, format="audio/wav")
                except Exception as e:
                    st.warning(f"Tätä tiedostoa ei voitu toistaa: {e}")

    except Exception as e:
        st.error(f"Virhe listan haussa: {e}")

# --- KÄYTTÖLIITTYMÄ ---

st.title("💾 Sukumuistot Talteen (v2.0)")
st.info(f"Yhteys kansioon: {TARGET_FOLDER_NAME}")

if 'current_question' not in st.session_state:
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

if st.button("🔄 Uusi kysymys"):
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

st.markdown(f"### 🗣️ {st.session_state['current_question']}")

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
    
    if st.button("Tallenna pilveen"):
        if not puhuja:
            st.warning("Kerro ensin kuka puhuu.")
        else:
            with st.spinner("Tallennetaan..."):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
                clean_name = "".join(x for x in puhuja if x.isalnum())
                filename = f"{timestamp}_{clean_name}_muisto.wav"
                
                if save_to_drive(wav_audio_data, filename):
                    st.success("Tallennettu!")
                    st.cache_data.clear() # Pakottaa listan päivityksen

st.divider()
list_and_play_files()
