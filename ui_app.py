"""Tableau de bord Streamlit pour la démonstration Pharmacie/Radiologie."""
import os

import grpc
import streamlit as st

from data.mock_pharmacie_radio import MEDICAMENTS
from grpc_services.generated import pharmacie_pb2, pharmacie_pb2_grpc
from grpc_services.generated import radiologie_pb2, radiologie_pb2_grpc


st.set_page_config(page_title="Clinique Espoir | Services", page_icon="🏥", layout="wide")
st.title("Clinique Espoir — Pharmacie & Radiologie")
st.caption("Tableau de démonstration connecté aux services gRPC locaux.")

with st.sidebar:
    st.header("Connexion gRPC")
    host = st.text_input("Hôte", value=os.getenv("GRPC_HOST", "localhost"))
    pharmacie_port = st.number_input("Port pharmacie", value=int(os.getenv("PHARMACIE_PORT", "50052")), step=1)
    radiologie_port = st.number_input("Port radiologie", value=int(os.getenv("RADIOLOGIE_PORT", "50053")), step=1)
    timeout = st.number_input("Délai max (secondes)", min_value=0.1, value=2.0, step=0.1)
    st.divider()

    def verifier_connexion(port):
        channel = grpc.insecure_channel(f"{host}:{int(port)}")
        try:
            grpc.channel_ready_future(channel).result(timeout=0.7)
            return True
        except grpc.FutureTimeoutError:
            return False
        finally:
            channel.close()

    pharmacie_en_ligne = verifier_connexion(pharmacie_port)
    radiologie_en_ligne = verifier_connexion(radiologie_port)
    st.markdown(f"Pharmacie : {'🟢 En ligne' if pharmacie_en_ligne else '🔴 Hors ligne'}")
    st.markdown(f"Radiologie : {'🟢 En ligne' if radiologie_en_ligne else '🔴 Hors ligne'}")
    if st.button("Actualiser l’état des services"):
        st.rerun()


def consulter_stock(medicament_id, quantite_demandee=None):
    request = pharmacie_pb2.VerifierStockRequest(medicament_id=medicament_id)
    if quantite_demandee is not None:
        request.quantite_demandee = quantite_demandee
    with grpc.insecure_channel(f"{host}:{int(pharmacie_port)}") as channel:
        return pharmacie_pb2_grpc.PharmacieServiceStub(channel).VerifierStock(request, timeout=timeout)


def consulter_examens(examen_id="", patient_id=""):
    request = radiologie_pb2.ObtenirExamenRequest(examen_id=examen_id, patient_id=patient_id)
    with grpc.insecure_channel(f"{host}:{int(radiologie_port)}") as channel:
        return radiologie_pb2_grpc.RadiologieServiceStub(channel).ObtenirExamen(request, timeout=timeout)


onglet_pharmacie, onglet_radiologie = st.tabs(["💊 Pharmacie", "🩻 Radiologie"])

with onglet_pharmacie:
    st.subheader("Disponibilité des médicaments")
    col_recherche, col_table = st.columns([1, 1.4])
    with col_recherche:
        med_id = st.selectbox(
            "Médicament", options=list(MEDICAMENTS),
            format_func=lambda identifiant: f"{identifiant} — {MEDICAMENTS[identifiant]['nom']}",
        )
        quantite = st.number_input("Quantité à vérifier", min_value=1, value=1, step=1)
        if st.button("Vérifier le stock", type="primary"):
            try:
                stock = consulter_stock(med_id, int(quantite))
                st.metric("Quantité en stock", stock.quantite)
                st.write(f"**État :** {stock.statut.replace('_', ' ').title()}")
                st.write(f"**Emplacement :** {stock.emplacement or 'Non renseigné'}")
                if stock.disponible:
                    st.success(stock.message)
                else:
                    st.warning(stock.message)
            except grpc.RpcError as erreur:
                st.error(f"gRPC {erreur.code().name} : {erreur.details()}")
    with col_table:
        st.markdown("**État des stocks**")
        if st.button("Charger les stocks depuis le service"):
            lignes = []
            try:
                for identifiant in MEDICAMENTS:
                    stock = consulter_stock(identifiant)
                    lignes.append({
                        "Code": stock.medicament_id,
                        "Médicament": stock.nom,
                        "Quantité": stock.quantite,
                        "Statut": stock.statut.replace("_", " ").title(),
                        "Emplacement": stock.emplacement,
                    })
                st.session_state["stocks"] = lignes
            except grpc.RpcError as erreur:
                st.error(f"gRPC {erreur.code().name} : {erreur.details()}")
        if "stocks" in st.session_state:
            st.dataframe(st.session_state["stocks"], use_container_width=True, hide_index=True)
        else:
            st.info("Cliquez sur « Charger les stocks depuis le service » pour interroger la pharmacie.")

with onglet_radiologie:
    st.subheader("Examens et comptes-rendus")
    type_recherche = st.radio("Rechercher par", ["Identifiant d’examen", "Identifiant patient"], horizontal=True)
    valeur = st.text_input("Identifiant", placeholder="Ex. RAD001 ou PAT001")
    if st.button("Consulter les examens", type="primary"):
        if not valeur.strip():
            st.warning("Saisissez un identifiant pour lancer la recherche.")
        else:
            try:
                if type_recherche == "Identifiant d’examen":
                    reponse = consulter_examens(examen_id=valeur.strip())
                else:
                    reponse = consulter_examens(patient_id=valeur.strip())
                st.dataframe([
                    {
                        "Examen": examen.examen_id,
                        "Patient": examen.patient_id,
                        "Type": examen.type_examen,
                        "État": examen.etat.replace("_", " ").title(),
                        "Date": examen.date,
                        "Compte-rendu": examen.resultat or "En attente de compte-rendu",
                    }
                    for examen in reponse.examens
                ], use_container_width=True, hide_index=True)
            except grpc.RpcError as erreur:
                st.error(f"gRPC {erreur.code().name} : {erreur.details()}")
