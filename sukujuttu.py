import streamlit as st
from audio_recorder_streamlit import audio_recorder
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io
import datetime
import random

# --- ASETUKSET ---
st.set_page_config(page_title="Sukumuistot v3.0", page_icon="💾")

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
    # Haetaan tunnukset
    creds_dict = dict(st.secrets)
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
        
        # --- KORJAUS 1: Upload suoraan muistista (ei temp-tiedostoa) ---
        # Luodaan "virtuaalinen tiedosto" muistiin
        fh = io.BytesIO(audio_bytes)
        
        # Käytetään MediaIoBaseUploadia, joka ymmärtää virtuaalitiedostot
        media = MediaIoBaseUpload(fh, mimetype='audio/wav', resumable=True)
        
        file_metadata = {'name': filename, 'parents': [folder_id]}
        
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
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
                    # --- KORJAUS 2: Download suoraan muistiin ---
                    request = service.files().get_media(fileId=item['id'])
                    
                    # Luodaan tyhjä puskuri muistiin
                    fh = io.BytesIO()
                    
                    # Ladataan data puskuriin käyttäen virallista Downloaderia
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    
                    # Kelataan puskuri alkuun, jotta st.audio voi lukea sen
                    fh.seek(0)
                    
                    st.audio(fh, format="audio/wav")
                    
                except Exception as e:
                    st.warning(f"Virhe toistossa: {e}")

    except Exception as e:
        st.error(f"Virhe listan haussa: {e}")

# --- KÄYTTÖLIITTYMÄ ---

st.markdown("<h1 style='text-align: center; color: #4F8BF9;'>💾 Sukumuistot v3.0</h1>", unsafe_allow_html=True)

if 'current_question' not in st.session_state:
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

if st.button("🔄 Vaihda kysymys"):
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

st.success(f"🗣️ {st.session_state['current_question']}")

# --- NAUHOITUS ---
st.write("Paina mikrofonia ja kerro tarina:")
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
            with st.spinner("Siirretään Driveen..."):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
                clean_name = "".join(x for x in puhuja if x.isalnum())
                # Lyhennetään kysymystä tiedostonimeen
                clean_q = st.session_state['current_question'][:10].replace(" ","_")
                
                filename = f"{timestamp}_{clean_name}_{clean_q}.wav"
                
                if save_to_drive(wav_audio_data, filename):
                    st.balloons()
                    st.success("Tallennettu onnistuneesti!")
                    # Pieni kikka: päivitetään sivu jotta uusi tiedosto näkyy listalla
                    import time
                    time.sleep(2)
                    st.rerun()

st.divider()
list_and_play_files()
