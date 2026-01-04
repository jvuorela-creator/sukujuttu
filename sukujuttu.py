import streamlit as st
from audio_recorder_streamlit import audio_recorder # <--- TÄMÄ VAIHTUI
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import random

# --- DEBUG ALKAA (poista tämä kun toimii) ---
try:
    user = st.secrets["EMAIL_USER"]
    pwd = st.secrets["EMAIL_PASSWORD"]
    st.warning(f"DEBUG: Yritetään lähettää tililtä: {user}")
    st.warning(f"DEBUG: Salasanan pituus on: {len(pwd)} merkkiä (pitäisi olla 16)")
except Exception as e:
    st.error(f"DEBUG VIRHE: Asetuksia ei löydy! {e}")
# --- DEBUG LOPPU ---

# --- ASETUKSET ---
st.set_page_config(page_title="Sukumuistot", page_icon="🎙️")

KYSYMYKSET = [
    "Kuka oli paras ystäväsi lapsuudessa?",
    "Mitä söitte jouluna, kun olit pieni?",
    "Kerro ensimmäisestä koulupäivästäsi.",
    "Millainen oli isäsi/äitisi luonne?",
    "Mikä on ollut elämäsi onnellisin hetki?",
    "Millaista oli asua lapsuudenkodissasi?",
]

# --- SÄHKÖPOSTIN LÄHETYSFUNKTIO ---
def send_email(recipient_email, subject, body, audio_data):
    try:
        sender_email = st.secrets["EMAIL_USER"]
        password = st.secrets["EMAIL_PASSWORD"]
    except FileNotFoundError:
        st.error("Sähköpostiasetukset (secrets) puuttuvat!")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Liitetään äänitiedosto
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(audio_data)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="muisto.wav"')
    msg.attach(part)

    try:
        # --- MUUTOS ALKAA TÄSTÄ ---
        # Käytetään SMTP_SSL ja porttia 465. Tämä on varmempi tapa pilvessä.
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        # Huom: server.starttls() -komentoa EI tarvita tässä.
        
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        # --- MUUTOS LOPPUU ---
        return True
    except Exception as e:
        # Tulostetaan tarkempi virheilmoitus ruudulle
        st.error(f"Virhe lähetyksessä: {e}")
        return False

# --- KÄYTTÖLIITTYMÄ ---

st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🎙️ Sukumuistot Talteen</h1>", unsafe_allow_html=True)
st.divider()

if 'current_question' not in st.session_state:
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

if st.button("🔄 Vaihda kysymys"):
    st.session_state['current_question'] = random.choice(KYSYMYKSET)

st.markdown(f"""
<div style='background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
    <h2 style='color: #333;'>{st.session_state['current_question']}</h2>
</div>
""", unsafe_allow_html=True)

# --- NAUHOITUS ---
st.subheader("1. Nauhoita vastaus")
st.write("Klikkaa mikrofonia nauhoittaaksesi. Klikkaa uudestaan lopettaaksesi.")

# --- TÄMÄ OSA VAIHTUI (Uusi kirjasto) ---
wav_audio_data = audio_recorder(
    text="",  # Ei tekstiä napin sisällä, vain ikoni
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="3x", # Iso mikrofoni
)
# ----------------------------------------

if wav_audio_data is not None:
    # Näytetään soitin, jotta voi tarkistaa nauhoituksen
    st.audio(wav_audio_data, format='audio/wav')
    
    st.subheader("2. Lähetä muisto talteen")
    
    with st.form("send_form"):
        recipient = st.text_input("Mihin sähköpostiin muisto lähetetään?", placeholder="esim. matti@suku.fi")
        submitted = st.form_submit_button("📤 LÄHETÄ MUISTO")
        
        if submitted and recipient:
            with st.spinner("Lähetetään muistoa..."):
                success = send_email(
                    recipient, 
                    f"Sukumuisto: {st.session_state['current_question']}", 
                    "Tässä on uusi nauhoitettu tarina liitteenä.", 
                    wav_audio_data
                )
                if success:
                    st.balloons()
                    st.success("Muisto lähetetty onnistuneesti sähköpostiin!")


