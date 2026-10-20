"""Tableau de bord Streamlit pour les services gRPC de la Clinique Espoir."""
import os

import grpc
import streamlit as st

from data.mock_pharmacie_radio import MEDICAMENTS
from grpc_services.clients import PharmacieClient, RadiologieClient, check_health


st.set_page_config(page_title="Clinique Espoir | Services", page_icon="🏥", layout="wide")
st.title("Clinique Espoir — Pharmacie & Radiologie")
st.caption("Panneau de démonstration connecté aux services gRPC configurés.")

with st.sidebar:
    st.header("Connexion gRPC")
    pharmacie_target = st.text_input(
        "Cible pharmacie", value=os.getenv("PHARMACIE_GRPC_TARGET", "localhost:50052")
    )
    radiologie_target = st.text_input(
        "Cible radiologie", value=os.getenv("RADIOLOGIE_GRPC_TARGET", "localhost:50053")
    )
    timeout = st.number_input("Délai maximal (secondes)", min_value=0.1, value=2.0, step=0.1)

    def verifier_connexion(target):
        return check_health(target, timeout=0.7)

    pharmacie_en_ligne = verifier_connexion(pharmacie_target)
    radiologie_en_ligne = verifier_connexion(radiologie_target)
    st.markdown(f"Pharmacie : {'🟢 En ligne' if pharmacie_en_ligne else '🔴 Hors ligne'}")
    st.markdown(f"Radiologie : {'🟢 En ligne' if radiologie_en_ligne else '🔴 Hors ligne'}")
    if st.button("Actualiser l’état des services"):
        st.rerun()

onglet_pharmacie, onglet_radiologie = st.tabs(["💊 Pharmacie", "🩻 Radiologie"])

with onglet_pharmacie:
    st.subheader("Disponibilité et stocks des médicaments")
    col_recherche, col_table = st.columns([1, 1.5])
    with col_recherche:
        med_id = st.selectbox(
            "Médicament", options=list(MEDICAMENTS),
            format_func=lambda identifiant: f"{identifiant} — {MEDICAMENTS[identifiant]['nom']}",
        )
        quantite = st.number_input("Quantité à vérifier", min_value=1, value=1, step=1)
        if st.button("Vérifier la disponibilité", type="primary"):
            try:
                with PharmacieClient(pharmacie_target, timeout) as client:
                    stock = client.verifier_stock(med_id, int(quantite))
                st.metric("Quantité en stock", stock.quantite)
                st.write(f"**État :** {stock.statut.replace('_', ' ').title()}")
                st.write(f"**Emplacement :** {stock.emplacement or 'Non renseigné'}")
                st.success(stock.message) if stock.disponible else st.warning(stock.message)
            except grpc.RpcError as erreur:
                st.error(f"gRPC {erreur.code().name} : {erreur.details()}")

        with st.expander("Ajuster le stock de démonstration"):
            nouvelle_quantite = st.number_input("Nouvelle quantité", min_value=0, value=0, step=1)
            if st.button("Enregistrer la quantité"):
                try:
                    with PharmacieClient(pharmacie_target, timeout) as client:
                        resultat = client.mettre_a_jour_stock(med_id, int(nouvelle_quantite))
                    st.success(f"Stock mis à jour : {resultat.quantite} unité(s), statut {resultat.statut}.")
                    st.session_state.pop("stocks", None)
                except grpc.RpcError as erreur:
                    st.error(f"gRPC {erreur.code().name} : {erreur.details()}")
            st.caption("Les stocks sont en mémoire et sont réinitialisés au redémarrage du serveur.")

    with col_table:
        st.markdown("**Inventaire servi par la pharmacie**")
        if st.button("Actualiser l’inventaire"):
            try:
                with PharmacieClient(pharmacie_target, timeout) as client:
                    liste = client.lister_medicaments()
                st.session_state["stocks"] = [
                    {
                        "Code": m.medicament_id,
                        "Médicament": m.nom,
                        "Quantité": m.quantite,
                        "Statut": m.statut.replace("_", " ").title(),
                        "Emplacement": m.emplacement,
                    }
                    for m in liste.medicaments
                ]
            except grpc.RpcError as erreur:
                st.error(f"gRPC {erreur.code().name} : {erreur.details()}")
        if "stocks" in st.session_state:
            st.dataframe(st.session_state["stocks"], use_container_width=True, hide_index=True)
        else:
            st.info("Actualisez l’inventaire pour charger les données depuis le service.")

with onglet_radiologie:
    st.subheader("Examens et comptes-rendus")
    type_recherche = st.radio("Rechercher par", ["Identifiant d’examen", "Identifiant patient"], horizontal=True)
    valeur = st.text_input("Identifiant", placeholder="Ex. RAD001 ou PAT001")
    if st.button("Consulter les examens", type="primary"):
        if not valeur.strip():
            st.warning("Saisissez un identifiant pour lancer la recherche.")
        else:
            try:
                with RadiologieClient(radiologie_target, timeout) as client:
                    if type_recherche == "Identifiant d’examen":
                        reponse = client.obtenir_examens(examen_id=valeur.strip())
                    else:
                        reponse = client.obtenir_examens(patient_id=valeur.strip())
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
