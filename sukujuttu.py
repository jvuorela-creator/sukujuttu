import streamlit as st
from audio_recorder_streamlit import audio_recorder
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload # <--- UUSI TUONTI
import io
import datetime
import random

# --- ASETUKSET ---
st.set_page_config(page_title="Sukumuistot Driveen", page_icon="💾")

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
    """Luo ja palauttaa Drive-yhteyden"""
    creds_dict = dict(st.secrets)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)

def get_folder_id(service, folder_name):
    """Etsii kansion ID:n nimen perusteella"""
    results = service.files().list(
        q=f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'",
        fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        return None
    return items[0]['id']

def save_to_drive(audio_bytes, filename):
    """Tallentaa tiedoston Driveen"""
    try:
        service = get_drive_service()
        folder_id = get_folder_id(service, TARGET_FOLDER_NAME)

        if not folder_id:
            st.error(f"Kansiota '{TARGET_FOLDER_NAME}' ei löytynyt!")
            return False
        
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(audio_bytes), mimetype='audio/wav')
        
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Virhe Drive-tallennuksessa: {e}")
        return False

def list_and_play_files():
    """Hakee viimeisimmät tiedostot ja näyttää soittimet"""
    try:
        service = get_drive_service()
        folder_id = get_folder_id(service, TARGET_FOLDER_NAME)
        
        if not folder_id:
            return

        # Haetaan kansion tiedostot (viimeiset 10)
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
            orderBy="createdTime desc",
            pageSize=10,
            fields="files(id, name, createdTime)").execute()
        
        items = results.get('files', [])

        if not items:
            st.info("Ei vielä tallennettuja muistoja.")
            return

        st.subheader("🎧 Kuuntele muiden muistoja")
        
        # Loopataan tiedostot läpi
        for item in items:
            with st.expander(f"📁 {item['name']}"):
                try:
                    # --- KORJAUS ALKAA ---
                    # Ladataan tiedosto suoraan muistiin yhtenä könttinä
                    # Tämä välttää "seekable bit stream" -virheen
                    file_content = service.files().get_media(fileId=item['id']).execute()
                    
                    # Soitetaan ääni
                    st.audio(file_content, format="audio/wav")
                    # --- KORJAUS LOPPUU ---
                    
                except Exception as e:
                    st.error(f"Virhe tämän tiedoston toistossa: {e}")

    except Exception as e:
        st.error(f"Virhe tiedostolistan hakemisessa: {e}")

# --- KÄYTTÖLIITTYMÄ ---

st.markdown("<h1 style='text-align: center; color: #2E86C1;'>💾 Sukumuistot Talteen</h1>", unsafe_allow_html=True)
st.caption(f"Tallennuspaikka: Google Drive / {TARGET_FOLDER_NAME}")

st.divider()

if 'current_question' not in st.session_state:
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

if st.button("🔄 Vaihda kysymys"):
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

st.markdown(f"""
<div style='background-color: #e8f4f8; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
    <h3 style='color: #333;'>{st.session_state['current_question']}</h3>
</div>
""", unsafe_allow_html=True)

# --- NAUHOITUS ---
st.write("🔴 Paina mikrofonia nauhoittaaksesi:")
wav_audio_data = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x",
)

if wav_audio_data is not None:
    st.audio(wav_audio_data, format='audio/wav')
    
    puhuja = st.text_input("Kuka puhuu?", placeholder="esim. Mummo")
    
    if st.button("💾 TALLENNA MUISTO"):
        if not puhuja:
            st.warning("Kirjoita puhujan nimi ensin.")
        else:
            with st.spinner("Tallennetaan pilveen..."):
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
                short_q = st.session_state['current_question'][:15].replace(" ", "_").replace("?", "")
                # Muotoillaan nimi selkeäksi: Pvm - Puhuja - Aihe
                filename = f"{timestamp} - {puhuja} - {short_q}.wav"
                
                success = save_to_drive(wav_audio_data, filename)
                
                if success:
                    st.balloons()
                    st.success("Tallennettu! Muisto ilmestyy pian alas listaan.")
                    # Tyhjennetään välimuisti, jotta uusi tiedosto näkyy heti
                    st.cache_data.clear()

st.divider()

# --- NÄYTÄ GALLERIA ---
# Tämä lataa ja näyttää tiedostot sivun alalaidassa
list_and_play_files()

