"""Jeux de données locaux de démonstration pour pharmacie et radiologie."""

MEDICAMENTS = {
    "MED001": {
        "nom": "Paracétamol 500 mg", "quantite": 120, "seuil_critique": 20,
        "emplacement": "Rayon A1", "statut": "disponible",
    },
    "MED002": {
        "nom": "Amoxicilline 1 g", "quantite": 0, "seuil_critique": 10,
        "emplacement": "Rayon B2", "statut": "rupture",
    },
    "MED003": {
        "nom": "Ibuprofène 400 mg", "quantite": 35, "seuil_critique": 15,
        "emplacement": "Rayon A3", "statut": "disponible",
    },
    "MED004": {
        "nom": "Sérum physiologique 500 ml", "quantite": 8, "seuil_critique": 12,
        "emplacement": "Réserve C1", "statut": "stock_critique",
    },
    "MED005": {
        "nom": "Artemether-luméfantrine 20/120 mg", "quantite": 46,
        "seuil_critique": 10, "emplacement": "Rayon D1", "statut": "disponible",
    },
    "MED006": {
        "nom": "Metformine 850 mg", "quantite": 27, "seuil_critique": 10,
        "emplacement": "Rayon B4", "statut": "disponible",
    },
    "MED007": {
        "nom": "Ceftriaxone 1 g", "quantite": 5, "seuil_critique": 8,
        "emplacement": "Réserve froide", "statut": "stock_critique",
    },
    "MED008": {
        "nom": "Solution de réhydratation orale", "quantite": 0,
        "seuil_critique": 15, "emplacement": "Rayon C2", "statut": "rupture",
    },
}

EXAMENS = {
    "RAD001": {
        "patient_id": "PAT001", "type_examen": "Radiographie thoracique",
        "etat": "termine", "resultat": "Aucune anomalie pulmonaire visible.",
        "date": "2026-10-18",
    },
    "RAD002": {
        "patient_id": "PAT002", "type_examen": "IRM cérébrale",
        "etat": "en_attente", "resultat": "", "date": "2026-10-20",
    },
    "RAD003": {
        "patient_id": "PAT001", "type_examen": "Scanner abdominal",
        "etat": "en_cours", "resultat": "Compte-rendu en cours de validation.",
        "date": "2026-10-20",
    },
    "RAD004": {
        "patient_id": "PAT003", "type_examen": "Radiographie du poignet droit",
        "etat": "termine", "resultat": "Fracture non déplacée du radius distal.",
        "date": "2026-10-16",
    },
    "RAD005": {
        "patient_id": "PAT004", "type_examen": "Scanner thoracique",
        "etat": "en_attente", "resultat": "", "date": "2026-10-21",
    },
    "RAD006": {
        "patient_id": "PAT002", "type_examen": "Radiographie du bassin",
        "etat": "termine", "resultat": "Pas de lésion osseuse aiguë détectée.",
        "date": "2026-10-19",
    },
    "RAD007": {
        "patient_id": "PAT005", "type_examen": "IRM lombaire",
        "etat": "en_cours", "resultat": "Acquisition des images en cours.",
        "date": "2026-10-20",
    },
}
