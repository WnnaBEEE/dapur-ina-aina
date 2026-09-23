import streamlit as st

st.title("Kontol")
nama = st.text_input("Masukkan Nama Anda\t:")
age = st.slider("Masukkan Umur Anda\t:", min_value=0, max_value=120, value=25)

if st.link_button("Link Jp", "https://missav.live/dm252/id"):
    st.write("Anda telah mengklik link!")
